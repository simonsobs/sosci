import os
import re
import sqlite3
from argparse import ArgumentParser, Namespace
from glob import glob
from logging import Logger
from pathlib import Path
from typing import List

from sotodlib.core.metadata import obsdb, obsfiledb

from sosci.transfers import rsync, globus

def metadata_update(db: str, outfile: Path, sub: List[str]) -> None:
    # If outfile is not specified, create a default outfile name
    if outfile is None:
        indir = os.path.dirname(db)
        inroot = os.path.basename(db)
        inname, _ = os.path.splitext(inroot)
        outfile = os.path.join(indir, f"{inname}_updated.sqlite")

    # Parse the path substitutions
    subs = list()
    for sarg in sub:
        oldpath, newpath = sarg.split(":")
        oldpath = oldpath.replace("/", "\/")
        subs.append(
            (
                re.compile(oldpath),
                newpath,
            )
        )
    if len(subs) == 0:
        print("No substitutions specified!")
        return

    # Temporary files
    temp_dump = f"{outfile}.temp_dump"
    temp_load = f"{outfile}.temp_load"
    temp_db = f"{outfile}.temp"

    outfile.parent.mkdir(parents=True, exist_ok=True)
    # Dump the database to a temporary file
    have_obsid = list()
    with open(temp_dump, "w") as tf:
        # Dump tables
        con = sqlite3.connect(db)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for row in cursor.fetchall():
            table = row[0]
            col_info = con.execute(f"PRAGMA table_info('{table}');").fetchall()
            for col in col_info:
                col_name = col[1]
                if col_name == "obs_id":
                    have_obsid.append(table)
        for line in con.iterdump():
            tf.write(f"{line}\n")
        con.close()

    # Pass through the dump file and replace paths
    with open(temp_load, "w") as tmod:
        with open(temp_dump, "r") as tf:
            for line in tf:
                for sreg, newpath in subs:
                    line = sreg.sub(newpath, line)
                tmod.write(line)
        # Add obs_id indices
        for table in have_obsid:
            tmod.write(
                f"CREATE INDEX IF NOT EXISTS idx_obs_id_column ON {table}(obs_id);\n"
            )

    # Create new DB
    with sqlite3.connect(temp_db) as newdb:
        with open(temp_load, "r") as tmod:
            sqlcom = tmod.read()
            newdb.executescript(sqlcom)

    # Move into place atomically
    os.replace(temp_db, outfile)

    # Clean up tempfiles
    os.remove(temp_load)
    os.remove(temp_dump)


def translate_context_file(ctx_file: str, ctx_newfile: str, destination_path: Path) -> None:
    with open(ctx_file, "r") as f:
        lines = f.readlines()
    with open(ctx_newfile, "w") as f:
        for line in lines:
            if "/so/" in line:
                f.write(
                    re.sub(
                        "/so/",
                        f"{str(destination_path.parent)}/",
                        line,
                    )
                )
            elif ".sqlite" in line:
                f.write(
                    re.sub(
                        ".sqlite",
                        "_local.sqlite",
                        line,
                    )
                )
            else:
                f.write(line)


def merge_move_databases(staged_path: Path, final_path: Path, logger: Logger) -> None:

    for staged_db in staged_path.glob("**/*.sqlite"):

        replace = True

        db = final_path / staged_db.relative_to(staged_path)
        # The output DB already exists.  Try to patch it.
        if re.match(r".*obsdb.*", str(staged_db)) is not None:
            original_db = obsdb.ObsDb(staged_db)
            target_db = obsdb.ObsDb(db)
            report = obsdb.diff_obsdbs(target_db, original_db)
            if not report["different"]:
                logger.info(f"DB {db}: Already in sync")
                replace = False
            elif report["patchable"]:
                logger.info(f"DB {db}: Patching to match upstream")
                obsdb.patch_obsdb(report["patch_data"], target_db)
                replace = False
            else:
                logger.warning(f"DB {db}: Cannot be patched, will overwrite.")
                logger.warning(
                    f"DB {db}: {report['unpatchable_reason']}: {report['detail']}"
                )
            del report
            del target_db
            del original_db
        elif re.match(r".*obsfiledb.*", str(staged_db)) is not None:
            original_db = obsfiledb.ObsFileDb(staged_db)
            target_db = obsfiledb.ObsFileDb(db)
            report = obsfiledb.diff_obsfiledbs(target_db, original_db)
            if not report["different"]:
                logger.info(f"DB {db}: Already in sync")
                replace = False
            elif report["patchable"]:
                logger.info(f"DB {db}: Patching to match upstream")
                obsfiledb.patch_obsfiledb(report["patch_data"], target_db)
                replace = False
            else:
                logger.warning(f"DB {db}: Cannot be patched, will overwrite.")
                logger.warning(
                    f"DB {db}: {report['unpatchable_reason']}: {report['detail']}"
                )
            del report
            del target_db
            del original_db

        if replace:
            # Overwrite atomically
            logger.info(f"DB {db}: Overwrite with updated version")
            os.replace(staged_db, db)
        else:
            # We patched it, delete the temp db
            os.remove(staged_db)

def get_parser(parser: ArgumentParser) -> ArgumentParser:
    """Create and return a sub-argument parser for metadata syncing."""
    parser.add_argument("--destination-path", "-d", help="The path that the metadata store is")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run for testing.",
    )
    return parser

def _main(args: Namespace, logger: Logger) -> None:

    # Move data first somehow

    # Start DB translation
    destination_path = Path(args.destination_path)
    logger.info("starting DB translation")
    logger.debug(f"destination_path: {destination_path}")
    logger.debug(f"destination_path.parent: {destination_path.parent}")
    for db_file in glob(f"{str(destination_path)}/**/*.sqlite", recursive=True):
        if "_local" in db_file:
            continue
        logger.debug(f"Processing DB file: {db_file}")
        metadata_newfile = db_file.split(".")
        metadata_newfile[0] = metadata_newfile[0] + "_local"
        metadata_newfile = Path(".".join(metadata_newfile))
        logger.info(f"Translating {db_file} with {str(destination_path.parent)}")
        metadata_update(
            db=db_file,
            sub=[f"/so/:{str(destination_path.parent)}/"],
            outfile=destination_path.parent / "metadata_staging" / metadata_newfile.relative_to(destination_path),
        )

    logger.info("DB translation completed")
    merge_move_databases(
        staged_path=destination_path.parent / "metadata_staging",
        final_path=destination_path,
        logger=logger,
    )
    logger.info("DB sync completed")

    # Start context files translation
    logger.info("starting context files translation")
    for ctx_file in glob(f"/{str(destination_path)}/**/*.yaml", recursive=True):
        if "_local" not in ctx_file:
            ctx_newfile = ctx_file.split(".")
            ctx_newfile[0] = ctx_newfile[0] + "_local"
            ctx_newfile = ".".join(ctx_newfile)
            logger.info(f"Translating {ctx_file} with {str(destination_path.parent)}")
            translate_context_file(ctx_file, ctx_newfile, destination_path)
    logger.info("Context files translation completed")
    logger.info("Metadata sync completed")
