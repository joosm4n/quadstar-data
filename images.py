# iterate through the folder
#   unzip a package
#   read data about it
#       - exposure
#       - timestamp
#       - num images
#       - MORE...
#
#   maybe

import datetime as dt
from dataclasses import dataclass, field
import typing
from pathlib import Path
import re

import sqlalchemy
from sqlalchemy.exc import IntegrityError

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# local modules
import images_sql as orm
import tiff_analyse as tiff


ImageSet = typing.NewType("ImageSet", None)
RawImage = typing.NewType("RawImage", None)


@dataclass
class RawImage:
    name: str
    exposure_ms: int
    temp: float
    timestamp_unix: float
    parent_set: ImageSet = field(init=False)
    stats: ImageStats

    def to_orm(self) -> orm.RawImage:
        obj = orm.RawImage(
            name=self.name,
            exposure_ms=self.exposure_ms,
            temp=self.temp,
            timestamp_unix=self.timestamp_unix,
        )
        obj.stats = self.stats.to_orm()
        return obj

    # Add analysed data


@dataclass
class ImageStats:
    median: float
    mean: float
    std: float
    var: float
    max: float
    min: float
    image: RawImage = field(init=False)

    @staticmethod
    def from_dict(stats: dict[str, float]):
        return ImageStats(
            median=stats["median"],
            mean=stats["mean"],
            std=stats["std"],
            var=stats["var"],
            max=stats["max"],
            min=stats["min"],
        )

    def to_orm(self) -> orm.ImageStats:

        return orm.ImageStats(
            median=self.median,
            mean=self.mean,
            std=self.std,
            var=self.var,
            max=self.max,
            min=self.min,
        )


def analyse_raw_image(image_path: Path) -> RawImage:

    # Image name format
    # Ex<exposure_us>_(<exposure_secs>)_Gain1.0_Temp<temp>_<unix_timestamp_float>
    # 00...........00_11.............11_2222222_33......33_44..................44

    image_name: str = image_path.stem
    parts: list[str] = image_name.split("_")

    exposure_ms: int = int(float(parts[1][1:-2]) * 1000)
    temp: float = float(parts[3][4:])
    timestamp: float = float(parts[4])

    stats: dict[str, float] = tiff.get_tiff_stats(image_path)
    img_stats: ImageStats = ImageStats.from_dict(stats)

    return RawImage(
        name=image_name,
        exposure_ms=exposure_ms,
        temp=temp,
        timestamp_unix=timestamp,
        stats=img_stats,
    )


def parse_fits_header(header_text: str) -> dict[str, str]:
    """Split a raw FITS header into a dict of keyword -> raw value string.

    Only handles the standard 'KEYWORD = value / comment' card format;
    COMMENT/HISTORY/blank cards are skipped here (handled separately).
    """
    parts: dict[str, str] = {}
    for line in header_text.splitlines():
        if len(line) < 9 or line[8:9] != "=":
            continue  # not a keyword=value card (COMMENT, END, blank, etc.)
        keyword = line[:8].strip()
        rest = line[9:]
        # Strip the trailing " / comment" part, respecting quoted strings.
        if rest.lstrip().startswith("'"):
            # quoted string value: find the closing quote
            stripped = rest.lstrip()
            end_quote = stripped.index("'", 1)
            value = stripped[1:end_quote]
        else:
            value = rest.split("/", 1)[0].strip()
        parts[keyword] = value
    return parts


@dataclass(frozen=True)
class SolveData:
    ra: float  # degrees
    dec: float  # degrees
    secpix: float  # image scale in arcsec/pixel
    date_iso: str

    ref_pixel_x: float
    ref_pixel_y: float
    ref_pixel_ra: float
    ref_pixel_dec: float
    pixel_size_x: float  # degrees
    pixel_size_y: float  # degrees
    img_twist_x: float
    img_twist_y: float

    cd_mtx: tuple[tuple[float, float], tuple[float, float]]

    solve_time_sec: float

    def to_orm(self) -> orm.SolveData:
        (a, b), (c, d) = self.cd_mtx
        return orm.SolveData(
            ra=self.ra,
            dec=self.dec,
            secpix=self.secpix,
            date_iso=self.date_iso,
            ref_pixel_x=self.ref_pixel_x,
            ref_pixel_y=self.ref_pixel_y,
            ref_pixel_ra=self.ref_pixel_ra,
            ref_pixel_dec=self.ref_pixel_dec,
            pixel_size_x=self.pixel_size_x,
            pixel_size_y=self.pixel_size_y,
            img_twist_x=self.img_twist_x,
            img_twist_y=self.img_twist_y,
            cd_mtx=[a, b, c, d],
            solve_time_sec=self.solve_time_sec,
        )


_SOLVE_TIME_RE = re.compile(r"Solved in ([\d.]+) sec")


def get_solve_data(file_path: Path) -> SolveData:
    wcs_str: str = file_path.open(mode="r").read()
    parts: dict[str, str] = parse_fits_header(wcs_str)

    solve_time: float | None = None
    for line in wcs_str.splitlines():
        if line.startswith("COMMENT"):
            m = _SOLVE_TIME_RE.search(line)
            if m:
                solve_time = float(m.group(1))
                break

    return SolveData(
        ra=float(parts["RA"]),
        dec=float(parts["DEC"]),
        secpix=float(parts["SECPIX"]),
        date_iso=parts["DATE-OBS"].strip(),
        ref_pixel_x=float(parts["CRPIX1"]),
        ref_pixel_y=float(parts["CRPIX2"]),
        ref_pixel_ra=float(parts["CRVAL1"]),
        ref_pixel_dec=float(parts["CRVAL2"]),
        pixel_size_x=float(parts["CDELT1"]),
        pixel_size_y=float(parts["CDELT2"]),
        img_twist_x=float(parts["CROTA1"]),
        img_twist_y=float(parts["CROTA2"]),
        cd_mtx=(
            (float(parts["CD1_1"]), float(parts["CD1_2"])),
            (float(parts["CD2_1"]), float(parts["CD2_2"])),
        ),
        solve_time_sec=solve_time or 0.0,
    )


@dataclass(frozen=True)
class ImageSet:
    name: str
    path: Path
    timestamp: dt.datetime
    exposure_ms: int
    num_images: int
    images: list[RawImage]
    solve_data: SolveData

    def __post_init__(self):
        for i in self.images:
            i.parent_set = self

    @property
    def is_solved(self) -> bool:
        return self.solve_data is not None

    def to_orm(self) -> orm.ImageSet:
        obj = orm.ImageSet(
            name=self.name,
            path=str(self.path),
            timestamp=self.timestamp,
            exposure_ms=self.exposure_ms,
            num_images=self.num_images,
        )
        obj.images = [img.to_orm() for img in self.images]
        if self.solve_data is not None:
            obj.solve_data = self.solve_data.to_orm()
        return obj


def parse_folder_date(ymd: str, hms: str) -> dt.datetime:

    # Folder date format
    # YYYYMMDD_HHMMSS
    year = ymd[0:4]
    month = ymd[4:6]
    day = ymd[6:8]

    hour = hms[0:2]
    min = hms[2:4]
    sec = hms[4:6]

    # print(f"{year} {month} {day} {hour} {min} {sec}")
    return dt.datetime(
        year=int(year),
        month=int(month),
        day=int(day),
        hour=int(hour),
        minute=int(min),
        second=int(sec),
    )


def analyse_image_set(folder_path: Path) -> ImageSet:

    # Folder name format
    # YYYYMMDD_HHMMSS_e-<exposure_secs>_g-1.0_n-<num_exposures>
    # 00000000_111111_22.............22_33333_44.............44

    if not folder_path.is_dir():
        raise TypeError("folder_path must be a directory to 'analyse_image_set'")

    folder_name: str = folder_path.name
    if folder_name.endswith((".done", ".solve", ".taking")):
        folder_name = folder_path.stem

    parts: list[str] = folder_name.split("_")

    exposure_len_secs: float = float(parts[2][2:])
    exposure_len_ms: int = int(exposure_len_secs * 1000)

    num_images: int = int(parts[4][2:])
    timestamp = parse_folder_date(parts[0], parts[1])

    solve: SolveData | None = None
    images: list[RawImage] = []
    for file in folder_path.iterdir():
        if file.is_file():
            match file.suffix:
                case ".tiff":
                    images.append(analyse_raw_image(file))
                case ".fits":
                    pass
                case ".ini":
                    pass
                case ".log":
                    pass
                case ".wcs":
                    solve = get_solve_data(file)

    return ImageSet(
        name=folder_name,
        path=folder_path.absolute(),
        timestamp=timestamp,
        exposure_ms=exposure_len_ms,
        num_images=num_images,
        images=images,
        solve_data=solve,
    )


@dataclass
class DataBase:
    name: str
    engine: sqlalchemy.Engine

    def add_img_set(self, img_set: ImageSet):
        orm_img_set = img_set.to_orm()
        with Session(self.engine) as session:
            session.add(orm_img_set)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                print(
                    f"[Warning] Unable to add ImageSet '{img_set.name}' as is already in database!"
                )


def open_database(db_filename: str) -> DataBase:
    engine = create_engine(db_filename)
    orm.Base.metadata.create_all(engine)
    return DataBase(name=db_filename, engine=engine)


def main():
    p: Path = Path("20260824_185310_e-5.0_g-1.0_n-5.done")
    # p: Path = Path("20260805_221654_e-0.5_g-1.0_n-5")
    image_set: ImageSet = analyse_image_set(p)
    # print(image_set)

    db: DataBase = open_database("sqlite:///observations.db")
    db.add_img_set(image_set)


if __name__ == "__main__":
    main()
