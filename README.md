# QuadStar Data Analysis 
### Usage:
```python
uv run quadstar-data [-h] [-f FILENAME | -d DIRECTORY] [-l] [-r] [-s SQLITE]
```

### Options:
  - -h, --help:\
&emsp;&emsp;&emsp;&emsp;show this help message and exit
  - -f, --filename:  FILENAME\
&emsp;&emsp;&emsp;&emsp;The .tar.zst file you want to unzip and get data from\
  - -d, --directory: DIRECTORY\
&emsp;&emsp;&emsp;&emsp;It is a folder that all your .tar.zst files are in, to get data from
  - -l, --leave-unzipped:\
&emsp;&emsp;&emsp;&emsp;Leaves the unzipped folder you are reading data from
  - -r, --raw-dir:\
&emsp;&emsp;&emsp;&emsp;The given files are unzipped directories so no unzipping is required
  - -s, --sqlite: SQLITE\
&emsp;&emsp;&emsp;&emsp;name of the sqlite db to write to, defaults to 'sqlite:///observations.db'.
