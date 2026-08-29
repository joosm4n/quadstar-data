from re import sub

import sqlalchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from dataclasses import dataclass
import argparse
from pathlib import Path

from . import images as img
from . import zipping
from . import images_sql as orm
from . import imu_data as imu


@dataclass
class DataBase:
    name: str
    engine: sqlalchemy.Engine

    def add_img_set(self, img_set: img.ImageSet | list[img.ImageSet]):
        if isinstance(img_set, img.ImageSet):
            img_set = [img_set]

        for iset in img_set:
            orm_img_set: orm.ImageSet = iset.to_orm()
            with Session(self.engine) as session:
                session.add(orm_img_set)
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    print(
                        f"[Warning] Unable to add ImageSet '{iset.name}' as is already in database!"
                    )

    def add_imu_data(self, imu_data: orm.IMUData | list[orm.IMUData]):
        if isinstance(imu_data, orm.IMUData):
            imu_data = [imu_data]

        with Session(self.engine) as session:
            for d in imu_data:
                session.add(d)

            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                print("[Warning] Unable to add IMUData as is already in database!")


def open_database(db_filename: str) -> DataBase:
    engine = create_engine(db_filename)
    orm.Base.metadata.create_all(engine)
    return DataBase(name=db_filename, engine=engine)


def quadstar_data(
    path: str, db_name: str, leave_unzipped: bool, is_directory: bool, raw_dir: bool
):
    p: Path = Path(path)
    db: DataBase = open_database(db_name)
    image_set: img.ImageSet
    unzipped: Path

    dirs: list[Path]
    if is_directory:
        if raw_dir:
            dirs = [subdir for subdir in p.iterdir() if subdir.is_dir()]
        else:
            dirs = [
                subdir for subdir in p.iterdir() if subdir.name.endswith(".tar.zst")
            ]
    else:
        dirs = [p]

    for subdir in dirs:
        if not raw_dir:
            unzipped = zipping.extract_tar_zst(subdir)
        else:
            unzipped = subdir

        image_set = img.analyse_image_set(unzipped)
        if not leave_unzipped and not raw_dir:
            zipping.delete_unzipped_folder(unzipped, True)
        db.add_img_set(image_set)


def quadstar_imu(csv_path: str, db_name: str):
    path: Path = Path(csv_path)
    db: DataBase = open_database(db_name)

    files: list[Path]
    if path.is_dir():
        files = [f for f in path.iterdir() if f.suffix == ".csv"]
    else:
        files = [path]

    for file in files:
        imu_data: list[orm.IMUData] = imu.read_imu_csv(file)
        db.add_imu_data(imu_data)


def quadstar_main():
    parser = argparse.ArgumentParser(prog="uv run quadstar-data", suggest_on_error=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-f", "--filename", help="The .tar.zst file you want to unzip and get data from"
    )
    group.add_argument(
        "-d",
        "--directory",
        help="It is a folder that all your .tar.zst files are in, to get data from",
    )
    group.add_argument(
        "-i",
        "--imu",
        help="A .csv file or folder with .csv files that has imu data in it",
    )
    parser.add_argument(
        "-l",
        "--leave-unzipped",
        action="store_true",
        help="Leaves the unzipped folder you are reading data from",
    )
    parser.add_argument(
        "-r",
        "--raw-dir",
        action="store_true",
        help="The given files are unzipped directories so no unzipping is required",
    )

    DEFAULT_DB_NAME: str = "sqlite:///observations.db"
    parser.add_argument(
        "-s",
        "--sqlite",
        help=f"name of the sqlite db to write to, defaults to '{DEFAULT_DB_NAME}'.",
        default=DEFAULT_DB_NAME,
    )
    args: argparse.Namespace = parser.parse_args()

    if args.imu:
        quadstar_imu(
            csv_path=args.imu,
            db_name=args.sqlite,
        )
        return

    is_dir: bool = False
    data_path: str | None = None

    if args.filename:
        data_path = args.filename

    if args.directory:
        is_dir = True
        data_path = args.directory

    quadstar_data(
        path=data_path or ".",
        db_name=args.sqlite,
        leave_unzipped=args.leave_unzipped,
        is_directory=is_dir,
        raw_dir=bool(args.raw_dir),
    )
