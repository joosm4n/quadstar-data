import datetime as dt
from pathlib import Path

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RawImage(Base):
    __tablename__ = "raw_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    exposure_ms: Mapped[int]
    temp: Mapped[float]
    timestamp_unix: Mapped[float]
    stats: Mapped["ImageStats | None"] = relationship(
        back_populates="image", uselist=False, cascade="all, delete-orphan"
    )

    parent_set_id: Mapped[int] = mapped_column(ForeignKey("image_sets.id"))
    parent_set: Mapped["ImageSet"] = relationship(back_populates="images")


class ImageStats(Base):
    __tablename__ = "image_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("raw_images.id"), unique=True)
    image: Mapped["RawImage"] = relationship(back_populates="stats")
    median: Mapped[float]
    mean: Mapped[float]
    std: Mapped[float]
    var: Mapped[float]
    max: Mapped[float]
    min: Mapped[float]


class SolveData(Base):
    __tablename__ = "solve_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    ra: Mapped[float]  # degrees
    dec: Mapped[float]  # degrees
    secpix: Mapped[float]  # arcsec/pixel
    date_iso: Mapped[str]
    ref_pixel_x: Mapped[float]
    ref_pixel_y: Mapped[float]
    ref_pixel_ra: Mapped[float]
    ref_pixel_dec: Mapped[float]
    pixel_size_x: Mapped[float]  # degrees
    pixel_size_y: Mapped[float]  # degrees
    img_twist_x: Mapped[float]
    img_twist_y: Mapped[float]
    solve_time_sec: Mapped[float]

    # 2x2 matrix flattened to a 4-element list, stored as JSON.
    # Works on SQLite, Postgres, MySQL alike (SQLite stores it as TEXT
    # under the hood and (de)serializes transparently).
    cd_mtx: Mapped[list[float]] = mapped_column(JSON)

    image_set_id: Mapped[int] = mapped_column(ForeignKey("image_sets.id"), unique=True)
    image_set: Mapped["ImageSet"] = relationship(back_populates="solve_data")

    @property
    def cd_matrix_tuple(self) -> tuple[tuple[float, float], tuple[float, float]]:
        a, b, c, d = self.cd_mtx
        return ((a, b), (c, d))


class ImageSet(Base):
    __tablename__ = "image_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    path: Mapped[str]  # store Path as str; wrap with Path(...) at the app layer
    timestamp: Mapped[dt.datetime]
    exposure_ms: Mapped[int]
    num_images: Mapped[int]

    images: Mapped[list["RawImage"]] = relationship(
        back_populates="parent_set", cascade="all, delete-orphan"
    )
    solve_data: Mapped["SolveData | None"] = relationship(
        back_populates="image_set", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def is_solved(self) -> bool:
        return self.solve_data is not None

    @property
    def path_obj(self) -> Path:
        return Path(self.path)


class IMUData(Base):
    __tablename__ = "imu_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[float]
    acel_x: Mapped[float]
    acel_y: Mapped[float]
    acel_z: Mapped[float]
    gyro_x: Mapped[float]
    gyro_y: Mapped[float]
    gyro_z: Mapped[float]

    @property
    def acel(self) -> tuple[float, float, float]:
        return (self.acel_x, self.acel_y, self.acel_z)

    @property
    def gyro(self) -> tuple[float, float, float]:
        return (self.gyro_x, self.gyro_y, self.gyro_z)
