"""Download IRS bulk data for population-level nonprofit analysis.

Sources:
- SOI Tax Stats: Annual financial extracts from Form 990 filings
- EO BMF: Exempt Organizations Business Master File (registry)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pandas as pd

from config import DATA_DIR
from forensics import sha256_file

IRS_SOI_BASE = "https://www.irs.gov/pub/irs-soi"
SOI_DIR = DATA_DIR / "irs" / "soi"
BMF_DIR = DATA_DIR / "irs" / "eo_bmf"
SOI_DIR.mkdir(parents=True, exist_ok=True)
BMF_DIR.mkdir(parents=True, exist_ok=True)


def download_soi(year: int = 2024) -> Path:
    """Download IRS SOI Tax Stats extract for Form 990 filers.

    Downloads ZIP, extracts CSV. Returns path to the CSV.
    """
    import zipfile

    csv_dest = SOI_DIR / f"soi_{year}_990.csv"
    if csv_dest.exists():
        print(f"  Already downloaded: {csv_dest.name} ({csv_dest.stat().st_size / 1_000_000:.1f}MB)")
        return csv_dest

    # IRS naming changed: 2018+ uses YYeoextract990.zip, older uses YYeofinextract990.zip
    yr = str(year)[2:]
    filenames = [
        f"{yr}eoextract990.zip",
        f"{yr}eofinextract990.zip",
    ]

    for filename in filenames:
        url = f"{IRS_SOI_BASE}/{filename}"
        zip_dest = SOI_DIR / filename

        print(f"  Trying: {url}")
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=180.0) as resp:
                if resp.status_code != 200:
                    continue
                with open(zip_dest, "wb") as f:
                    for chunk in resp.iter_bytes(8192):
                        f.write(chunk)

            # Extract CSV from ZIP
            with zipfile.ZipFile(zip_dest, "r") as zf:
                csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if not csv_names:
                    print(f"  No CSV found in {filename}")
                    continue
                # Extract the largest CSV (the main data file)
                csv_name = max(csv_names, key=lambda n: zf.getinfo(n).file_size)
                print(f"  Extracting: {csv_name}")
                with zf.open(csv_name) as src, open(csv_dest, "wb") as dst:
                    dst.write(src.read())

            # Clean up ZIP
            zip_dest.unlink()

            file_hash = sha256_file(csv_dest)
            size_mb = csv_dest.stat().st_size / 1_000_000
            print(f"  Extracted: {csv_dest.name} ({size_mb:.1f}MB, SHA-256: {file_hash[:16]}...)")

            # Save provenance
            (csv_dest.parent / f"{csv_dest.stem}_provenance.json").write_text(
                f'{{"url": "{url}", "sha256": "{file_hash}", "size_bytes": {csv_dest.stat().st_size}}}'
            )
            return csv_dest
        except Exception as e:
            print(f"  Failed: {e}")
            for p in [zip_dest, csv_dest]:
                if p.exists():
                    p.unlink()

    raise FileNotFoundError(f"Could not download SOI data for {year}")


def download_bmf(state: str = "pa") -> Path:
    """Download IRS EO Business Master File for a state.

    Returns the path to the downloaded CSV.
    """
    url = f"{IRS_SOI_BASE}/eo_{state.lower()}.csv"
    dest = BMF_DIR / f"eo_{state.lower()}.csv"

    if dest.exists():
        print(f"  Already downloaded: {dest.name}")
        return dest

    print(f"  Downloading BMF for {state.upper()}: {url}")
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=60.0)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        file_hash = sha256_file(dest)
        print(f"  Downloaded: {dest.name} (SHA-256: {file_hash[:16]}...)")
        return dest
    except Exception as e:
        raise FileNotFoundError(f"Could not download BMF for {state}: {e}")


def download_bmf_national() -> Path:
    """Download the combined national EO BMF for org name lookups.

    The IRS publishes state-by-state files. We download and combine them.
    """
    combined_path = BMF_DIR / "eo_national.csv"
    if combined_path.exists():
        print(f"  Already downloaded: {combined_path.name} ({combined_path.stat().st_size / 1_000_000:.1f}MB)")
        return combined_path

    # Download each state file and concatenate
    states = [
        "al", "ak", "az", "ar", "ca", "co", "ct", "de", "dc", "fl",
        "ga", "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me",
        "md", "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh",
        "nj", "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "pr",
        "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
        "wi", "wy",
    ]

    frames = []
    for state in states:
        url = f"{IRS_SOI_BASE}/eo_{state}.csv"
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=30.0)
            if resp.status_code == 200:
                state_path = BMF_DIR / f"eo_{state}.csv"
                state_path.write_bytes(resp.content)
                state_df = pd.read_csv(state_path, low_memory=False)
                frames.append(state_df)
                print(f"  {state.upper()}: {len(state_df):,} orgs")
        except Exception:
            print(f"  {state.upper()}: failed")

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined.to_csv(combined_path, index=False)
        print(f"  Combined: {len(combined):,} organizations saved to {combined_path.name}")
        return combined_path
    raise FileNotFoundError("Could not download BMF data")


def load_soi(year: int = 2024) -> pd.DataFrame:
    """Load SOI Tax Stats extract joined with BMF names.

    Downloads first if not already available.
    """
    path = SOI_DIR / f"soi_{year}_990.csv"
    if not path.exists():
        path = download_soi(year)

    df = pd.read_csv(path, low_memory=False)

    # Standardize column names (IRS uses inconsistent casing)
    df.columns = [c.strip().lower() for c in df.columns]

    # The SOI extract has EINs but no names. Join with BMF for names.
    bmf_path = BMF_DIR / "eo_national.csv"
    if bmf_path.exists():
        bmf = pd.read_csv(bmf_path, low_memory=False, usecols=lambda c: c.upper() in [
            "EIN", "NAME", "CITY", "STATE", "NTEE_CD", "SUBSECTION",
        ])
        bmf.columns = [c.strip().lower() for c in bmf.columns]
        bmf["ein"] = pd.to_numeric(bmf["ein"], errors="coerce")
        df["ein"] = pd.to_numeric(df["ein"], errors="coerce")

        # Merge names/state/ntee from BMF onto SOI data
        df = df.merge(bmf[["ein", "name", "city", "state", "ntee_cd"]].drop_duplicates("ein"),
                      on="ein", how="left", suffixes=("", "_bmf"))

    # Ensure numeric columns are numeric
    numeric_cols = [
        "totrevenue", "totfuncexpns", "compnsatncurrofcr", "othrsalwages",
        "totcntrbgfts", "totprgmrevnue", "totassetsend", "totliabend",
        "profndraising", "grsincfndrsng", "payrolltx", "invstmntinc",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def load_bmf(state: str = "pa") -> pd.DataFrame:
    """Load EO Business Master File into a pandas DataFrame."""
    path = BMF_DIR / f"eo_{state.lower()}.csv"
    if not path.exists():
        path = download_bmf(state)

    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip().lower() for c in df.columns]
    return df
