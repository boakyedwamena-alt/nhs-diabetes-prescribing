"""Download diabetes-drug rows (BNF section 6.1) from the NHSBSA English Prescribing Dataset
(EPD) with SNOMED code, keeping only those rows so you never store the full ~17M-row months.

  python -m src.download_epd                     # the default window, Apr 2023 to Mar 2024
  python -m src.download_epd --months 202401 202402
  python -m src.download_epd --from-csv path/to/epd_snomed_202401.csv   # file you downloaded by hand

Each monthly CSV is streamed and filtered in chunks. Output: data/raw/epd/epd_<YYYYMM>.csv.
Months already present are skipped, so an interrupted run can simply be restarted.

The resource ids below were read from the portal's dataset page
(https://opendata.nhsbsa.net/dataset/english-prescribing-dataset-epd-with-snomed-code).
The original EPD without SNOMED codes is retired, so do not use it.
"""
import argparse
import csv
import time
from pathlib import Path

import pandas as pd
import requests
import urllib3

from src.config import ROOT

OUT = ROOT / "data" / "raw" / "epd"
URL = ("https://opendata.nhsbsa.net/dataset/906115a6-4155-44be-8b81-f8e83cebfb84/"
       "resource/{rid}/download/epd_snomed_{ym}.csv")

RESOURCES = {
    "202304": "d621e74c-1118-4cde-a865-f07af62c9281", "202305": "300da531-b978-4bd7-9d6e-582b28385ff2",
    "202306": "2a83a077-2337-4111-9d24-a91b87aafa5f", "202307": "87fee4ef-8c70-4036-93fd-0cc64dfb98ef",
    "202308": "759994f4-cadd-4e9c-8b3c-73d31ffdfbdc", "202309": "7470b1e8-bf54-4cb2-a7bb-7b6133d45459",
    "202310": "f4cbbd4e-02c0-4f5e-83e7-407997877f37", "202311": "36c67aba-0ba4-402e-9182-f30a8cd9b138",
    "202312": "bb27b92e-f839-48f9-befc-5840964cc974", "202401": "e43050cd-815b-478e-916a-91952448d5bf",
    "202402": "82c3c694-e129-4542-a464-93d7328976fa", "202403": "2e950c3e-37a5-45bb-b81d-41ef9c0f2898",
}
BNF_COLUMNS = ("BNF_PRESENTATION_CODE", "BNF_CODE")  # new name first, old name as fallback


def filter_chunks(reader) -> pd.DataFrame:
    parts = []
    for chunk in reader:
        col = next((c for c in chunk.columns if c.upper() in BNF_COLUMNS), None)
        if col is None:
            raise ValueError(f"No BNF code column found. Headers: {list(chunk.columns)}")
        parts.append(chunk[chunk[col].str.startswith("0601", na=False)])
    return pd.concat(parts, ignore_index=True)


MAX_STALLS = 8          # consecutive failures with no progress before giving up on a month
CHUNK = 1024 * 1024


class _Restart(Exception):
    """The server ignored a resume request, so the month must be re-read from the start."""


def _lines(resp):
    """Yield complete raw lines (bytes, newline included) from a streaming response."""
    buf = b""
    for chunk in resp.iter_content(chunk_size=CHUNK):
        buf += chunk
        *done, buf = buf.split(b"\n")
        for ln in done:
            yield ln + b"\n"
    if buf:
        yield buf


class _Counter:
    """Hands lines to the CSV parser while counting the bytes consumed."""
    def __init__(self, lines):
        self.lines, self.nbytes = lines, 0

    def __iter__(self):
        return self

    def __next__(self):
        ln = next(self.lines)
        self.nbytes += len(ln)
        return ln.decode("utf-8", errors="replace")


def _open(ym: str, offset: int):
    headers = {"Accept-Encoding": "identity"}  # keep byte counts equal to file bytes
    if offset:
        headers["Range"] = f"bytes={offset}-"
    r = requests.get(URL.format(rid=RESOURCES[ym], ym=ym), headers=headers, stream=True, timeout=(30, 120))
    try:
        r.raise_for_status()
        if offset and r.status_code != 206:
            raise _Restart()
        if offset:
            total = int(r.headers["Content-Range"].split("/")[-1])
        else:
            total = int(r.headers.get("Content-Length", 0))
    except BaseException:
        r.close()
        raise
    return r, total


def fetch_month(ym: str) -> bool:
    """Stream one month, keep BNF 0601 rows, and resume after dropped connections.

    The EPD files are 4 to 8 GB and connections do drop. After a failure the download continues
    from the last complete row (an HTTP Range request) rather than starting again. The output only
    appears under its final name once the whole file has been read and its size checked.
    """
    target = OUT / f"epd_{ym}.csv"
    if target.exists():
        print(f"{ym}: already downloaded, skipping")
        return True
    tmp = target.with_suffix(".tmp")
    offset = total = kept = stalls = 0
    header = bnf_idx = out = writer = None
    print(f"{ym}: downloading (several GB, expect 10 to 40 minutes)...", flush=True)
    while True:
        base, resp = offset, None
        try:
            resp, size = _open(ym, offset)
            total = total or size
            counter = _Counter(_lines(resp))
            reader = csv.reader(counter)
            if header is None:  # first connection: read the header row
                header = next(reader)
                header[0] = header[0].lstrip("\ufeff")
                bnf_idx = next((i for i, c in enumerate(header) if c.upper() in BNF_COLUMNS), None)
                if bnf_idx is None:
                    raise ValueError(f"No BNF code column found. Headers: {header}")
                out = open(tmp, "w", newline="", encoding="utf-8")
                writer = csv.writer(out, lineterminator="\n")
                writer.writerow(header)
                offset = base + counter.nbytes
            last = time.time()
            for row in reader:
                if len(row) > bnf_idx and row[bnf_idx].startswith("0601"):
                    writer.writerow(row)
                    kept += 1
                offset = base + counter.nbytes  # everything up to here is safely written
                stalls = 0
                if time.time() - last > 30:
                    pct = f"{100 * offset / total:.0f}%" if total else "?"
                    print(f"{ym}: {pct} read, {kept:,} diabetes rows kept", flush=True)
                    last = time.time()
            if total and offset < total:
                raise OSError(f"stream ended early ({offset:,} of {total:,} bytes)")
            out.close()
            tmp.replace(target)
            print(f"{ym}: kept {kept:,} diabetes rows -> {target.name}")
            return True
        except _Restart:
            print(f"{ym}: server cannot resume, starting this month again from the beginning", flush=True)
            if out:
                out.close()
            offset = total = kept = 0
            header = bnf_idx = out = writer = None
            stalls += 1
        except (requests.RequestException, urllib3.exceptions.HTTPError, OSError) as e:
            stalls += 1
            if stalls > MAX_STALLS:
                print(f"{ym}: giving up after repeated failures ({type(e).__name__}).", flush=True)
                if out:
                    out.close()
                return False
            wait = min(15 * stalls, 120)
            print(f"{ym}: connection problem ({type(e).__name__}); resuming from "
                  f"{100 * offset / total:.0f}% in {wait}s..." if total else
                  f"{ym}: connection problem ({type(e).__name__}); retrying in {wait}s...", flush=True)
            time.sleep(wait)
        finally:
            if resp is not None:
                resp.close()


def from_csv(path: Path) -> None:
    df = filter_chunks(pd.read_csv(path, dtype=str, chunksize=500_000))
    ym_col = next(c for c in df.columns if c.upper() == "YEAR_MONTH")
    ym = str(df[ym_col].iloc[0]).replace("-", "")
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"epd_{ym}.csv", index=False)
    print(f"Wrote {len(df):,} rows for {ym}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", nargs="*", choices=sorted(RESOURCES), help="YYYYMM; default is all 12")
    ap.add_argument("--from-csv", type=Path)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.from_csv:
        from_csv(a.from_csv)
        return
    failed = [ym for ym in (a.months or sorted(RESOURCES)) if not fetch_month(ym)]
    if failed:
        print(f"\nStill missing: {', '.join(failed)}. Run the same command again later; "
              "finished months are skipped.")
    else:
        print("\nAll months downloaded.")


if __name__ == "__main__":
    main()
