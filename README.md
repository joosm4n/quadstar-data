usage: QuadStar Data Analysis [-h] [-f FILENAME | -d DIRECTORY] [-l] [-r]
                              [-s SQLITE]

options:
  -h, --help            show this help message and exit
  -f, --filename FILENAME
                        The .tar.zst file you want to unzip and get data from
  -d, --directory DIRECTORY
                        It is a folder that all your .tar.zst files are in, to
                        get data from
  -l, --leave-unzipped  Leaves the unzipped folder you are reading data from
  -r, --raw-dir         The given files are unzipped directories so no
                        unzipping is required
  -s, --sqlite SQLITE   name of the sqlite db to write to, defaults to
                        'sqlite:///observations.db'.
