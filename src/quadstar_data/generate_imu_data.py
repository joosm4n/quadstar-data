import random
import csv
import datetime

with open("test_imu.csv", "a") as f:
    writer = csv.writer(f)
    init_time: datetime.datetime = datetime.datetime.now()
    for _ in range(100):
        ts_str: str = (
            f"{(init_time + datetime.timedelta(seconds=0.25)).timestamp():.4f}"
        )
        writer.writerow(
            [
                ts_str,
                random.random(),
                random.random(),
                random.random(),
                random.random(),
                random.random(),
                random.random(),
            ]
        )
