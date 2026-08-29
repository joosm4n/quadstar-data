import csv
from pathlib import Path
from . import images_sql as orm


def read_imu_csv(path: Path) -> list[orm.IMUData]:
    all_rows: list[orm.IMUData] = []
    with open(path, "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            imu_data: orm.IMUData = orm.IMUData()
            imu_data.timestamp = float(row[0])
            imu_data.acel_x = float(row[1])
            imu_data.acel_y = float(row[2])
            imu_data.acel_z = float(row[3])
            imu_data.gyro_x = float(row[4])
            imu_data.gyro_y = float(row[5])
            imu_data.gyro_z = float(row[6])
            all_rows.append(imu_data)

    return all_rows
