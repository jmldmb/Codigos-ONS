import argparse
import datetime as dt
import os
from pathlib import Path
from typing import Iterable, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = (
    "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/energia_vertida_turbinavel_ho"
)


def build_yearly_urls(start_year: int, end_year_inclusive: int) -> List[Tuple[int, str]]:
    years = range(start_year, end_year_inclusive + 1)
    return [
        (year, f"{BASE_URL}/ENERGIA_VERTIDA_TURBINAVEL_{year}.parquet") for year in years
    ]


def build_monthly_urls(start_year: int, end_year_inclusive: int) -> List[Tuple[int, str]]:
    urls: List[Tuple[int, str]] = []
    current_year = dt.date.today().year
    current_month = dt.date.today().month

    for year in range(start_year, end_year_inclusive + 1):
        max_month = 12
        if year == current_year:
            max_month = current_month
        for month in range(1, max_month + 1):
            urls.append(
                (
                    year,
                    f"{BASE_URL}/ENERGIA_VERTIDA_TURBINAVEL_{year}_{month:02d}.parquet",
                )
            )
    return urls


def create_session(total_retries: int = 5, backoff: float = 0.5) -> requests.Session:
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "vertimento-downloader/1.0"})
    return session


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download_file(session: requests.Session, url: str, output_path: Path) -> bool:
    try:
        with session.get(url, stream=True, timeout=(10, 60)) as response:
            if response.status_code != 200:
                return False

            ensure_directory(output_path.parent)
            content_length = int(response.headers.get("Content-Length", "0") or 0)
            bytes_read = 0
            chunk_size = 1024 * 1024  # 1 MB

            tmp_path = output_path.with_suffix(output_path.suffix + ".part")
            with open(tmp_path, "wb") as file_handle:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # filter out keep-alive chunks
                        file_handle.write(chunk)
                        bytes_read += len(chunk)

            os.replace(tmp_path, output_path)

            # Simple progress message (only when content length is available)
            if content_length > 0:
                percent = (bytes_read / content_length) * 100
                print(f"Saved {output_path.name} ({percent:.1f}% of {content_length/1_048_576:.2f} MB)")
            else:
                print(f"Saved {output_path.name} ({bytes_read/1_048_576:.2f} MB)")
            return True
    except Exception as exc:  # noqa: BLE001 - top-level I/O guard
        print(f"Error downloading {url}: {exc}")
        return False


def generate_download_plan(
    yearly_start: int = 2015,
    yearly_end: int = 2022,
    monthly_start: int = 2023,
    monthly_end: int | None = None,
) -> List[Tuple[int, str, str]]:
    if monthly_end is None:
        monthly_end = dt.date.today().year

    plan: List[Tuple[int, str, str]] = []

    for year, url in build_yearly_urls(yearly_start, yearly_end):
        filename = f"ENERGIA_VERTIDA_TURBINAVEL_{year}.parquet"
        plan.append((year, url, filename))

    for year, url in build_monthly_urls(monthly_start, monthly_end):
        # filename includes month already in the URL
        filename = url.rsplit("/", 1)[-1]
        plan.append((year, url, filename))

    return plan


def run_download(
    output_root: Path,
    skip_existing: bool = True,
    verbose: bool = True,
) -> None:
    output_root = output_root.resolve()
    session = create_session()

    plan = generate_download_plan()

    print(
        f"Starting download of Vertimento Turbinavel parquet files to: {output_root}"
    )

    total = len(plan)
    completed = 0
    for idx, (year, url, filename) in enumerate(plan, start=1):
        year_dir = output_root / "energia_vertida_turbinavel" / f"{year}"
        out_path = year_dir / filename

        if skip_existing and out_path.exists():
            if verbose:
                print(f"[{idx}/{total}] Skipping existing: {out_path.name}")
            completed += 1
            continue

        if verbose:
            print(f"[{idx}/{total}] Downloading: {url}")

        ok = download_file(session, url, out_path)
        if not ok:
            print(f"[{idx}/{total}] Not available (HTTP {url})")
        else:
            completed += 1

    print(f"Done. {completed}/{total} files present/downloaded.")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa os arquivos Parquet de energia vertida turbinável (ONS) "
            "para 2015-2022 (anual) e 2023-atual (mensal)."
        )
    )
    default_output = (
        Path(__file__).resolve().parents[1] / "data" / "raw" / "vertimento"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Diretório de saída (default: {default_output})",
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Não ignorar arquivos já existentes (por padrão são ignorados)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Silencia mensagens informativas",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    ensure_directory(args.output)
    run_download(
        output_root=args.output,
        skip_existing=not args.no_skip_existing,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()


