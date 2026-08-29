import zstandard as zstd
import tarfile
from pathlib import Path
from shutil import rmtree


# all zipped with
# tar -I 'zstd -5' -cf "$archive" "$name"
def extract_tar_zst(archive_path: Path) -> Path:
    try:
        extract_root: Path = archive_path.absolute().parent
        dctx = zstd.ZstdDecompressor()
        top_level_dirs: set[str] = set()

        with open(archive_path, "rb") as compressed:
            with dctx.stream_reader(compressed) as reader:
                with tarfile.open(fileobj=reader, mode="r|") as tar:
                    for member in tar:
                        top_level_dirs.add(Path(member.name).parts[0])
                        tar.extract(member, path=extract_root)

        if len(top_level_dirs) != 1:
            raise ValueError("Bad extract")

        return extract_root / top_level_dirs.pop()

    except (tarfile.TarError, zstd.ZstdError) as e:
        print(f"Failed to unzip {archive_path}, due to: {e}")
        raise e


def delete_unzipped_folder(dir_path: Path, safety_check: bool = False):
    if safety_check is False:
        raise UserWarning(
            f"If you are sure you want to delete '{dir_path}' add 'safety_check = True' to function call"
        )

    check: bool = dir_path.is_dir() and not dir_path.is_symlink()
    if not check:
        raise TypeError(
            f"Unable to delete '{dir_path}', it has to be a folder and not a symlink!"
        )

    rmtree(
        path=dir_path,
    )
