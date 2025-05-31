import os
import shutil
import logging

from cmdClient import Context

from logger import log
from utils import ctx_addons  # noqa

from ..module import latex_module as module

from ..resources import default_preamble, failed_image_path, compile_script_path

"""
Provides a single context utility to compile LaTeX code from a user and return any error message
"""

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def gencolour(bgcolour, textcolour):
    """
    Build the colour definition commands for the provided colourscheme
    """
    return r"\def\texit@bgcolor{{{}}} \def\texit@textcolor{{{}}}".format(bgcolour, textcolour)


# Dictionary of valid colours and the associated transformation commands
colourschemes = {}

colourschemes["white"] = gencolour("ffffff", "000000")
colourschemes["black"] = gencolour("000000", "ffffff")

colourschemes["light"] = gencolour("dfdfdf", "1d1d1d")
colourschemes["dark"] = gencolour("141414", "eeeeee")

colourschemes["gray"] = colourschemes["grey"] = gencolour("313338", "ffffff")
colourschemes["darkgrey"] = gencolour("23272a", "ffffff")

colourschemes["trans_white"] = gencolour("trans", "ffffff")
colourschemes["trans_black"] = gencolour("trans", "000000")
colourschemes["transparent"] = colourschemes["trans_white"]

colourschemes["default"] = colourschemes["grey"]



# Header for every LaTeX source file
header = "\\documentclass{texit}\
    \n\\IfFileExists{eggs.sty}{\\usepackage{eggs}}{}\
    \n\\nonstopmode"

"""
# Alternative header to support discord emoji, but not other unicode
header = "\\documentclass[preview, border=20pt, 12pt]{standalone}\
    \n\\IfFileExists{eggs.sty}{\\usepackage{eggs}}{}\
    \n\\usepackage{discord-emoji}
    \n\\nonstopmode"
"""

# The format of the source to compile
to_compile = "\\makeatletter\
    \n{colour}\
    \n{alwayswide}\
    \n\\makeatother\
    \n{header}\
    \n{preamble}\
    \n\\begin{{document}}\
    \n{source}\
    \n\\end{{document}}"


@Context.util
async def makeTeX(ctx, source, targetid, preamble=default_preamble, colour="default", header=header, pad=True):
    log(
        "Beginning LaTeX compilation for (tid:{targetid}).\n{content}".format(
            targetid=targetid,
            content='\n'.join(('\t' + line for line in source.splitlines()))
        ),
        level=logging.DEBUG,
        context="mid:{}".format(ctx.msg.id) if ctx.msg else "tid:{}".format(targetid)
    )

    # Target's staging directory
    path = "tex/staging/{}".format(targetid)

    # Remove the staging directory, if it exists
    shutil.rmtree(path, ignore_errors=True)

    # Recreate staging directory
    os.makedirs(path, exist_ok=True)

    fn = "{}/{}.tex".format(path, targetid)

    with open(fn, 'w') as work:
        work.write(to_compile.format(colour=colourschemes[colour] or "",
                                     alwayswide="\\def\\texit@alwayswide{0}" if pad else "\\def\\texit@alwayswide{1}",
                                     header=header, preamble=preamble, source=source))
        work.close()

    # Build compile script
    script = (
        "{compile_script} {id} || exit;\n"
        "cd {path}\n").format(compile_script=compile_script_path,
                        id=targetid, path=path).format(image="{}.png".format(targetid))

    # Run the script in an async executor
    return await ctx.run_in_shell(script)


@module.init_task
def setup_structure(client):
    """
    Set up the initial tex directory structure,
    including copying the required resources.
    """
    # Delete and recreate the staging directory, if it exists
    shutil.rmtree("tex/staging", ignore_errors=True)
    os.makedirs("tex/staging", exist_ok=True)
    shutil.copy(failed_image_path, "tex")
