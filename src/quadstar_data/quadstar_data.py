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


@dataclass
class DataBase:
    name: str
    engine: sqlalchemy.Engine

    def add_img_set(self, img_set: img.ImageSet):
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


def quadstar_data(
    path: str, db_name: str, leave_unzipped: bool, is_directory: bool, raw_dir: bool
):
    p: Path = Path(path)
    db: DataBase = open_database(db_name)
    image_set: img.ImageSet
    unzipped: Path

    if is_directory:
        for subdir in p.iterdir():
            if not raw_dir:
                unzipped = zipping.extract_tar_zst(subdir)
            else:
                unzipped = subdir

            image_set = img.analyse_image_set(unzipped)
            if not leave_unzipped and not raw_dir:
                zipping.delete_unzipped_folder(unzipped, True)
            db.add_img_set(image_set)

    else:
        if not raw_dir:
            unzipped = zipping.extract_tar_zst(p)
        else:
            unzipped = p

        image_set = img.analyse_image_set(unzipped)
        if not leave_unzipped and not raw_dir:
            zipping.delete_unzipped_folder(unzipped, True)
        db.add_img_set(image_set)


def quadstar_main():
    parser = argparse.ArgumentParser(
        prog="QuadStar Data Analysis",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-f", "--filename", help="The .tar.zst file you want to unzip and get data from"
    )
    group.add_argument(
        "-d",
        "--directory",
        help="It is a folder that all your .tar.zst files are in, to get data from",
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
