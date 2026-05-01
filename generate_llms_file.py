"""Copy the llms.txt file to the generated site files for MkDocs when building documentation."""

from pathlib import Path

import mkdocs_gen_files


with mkdocs_gen_files.open("llms.txt", "wb") as dest:
    dest.write(Path("llms.txt").read_bytes())
