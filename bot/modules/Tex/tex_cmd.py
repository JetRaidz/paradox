from .module import latex_module as module

from .core.LatexContext import LatexContext
from .core.LatexGuild import LatexGuild
from .core.LatexUser import LatexUser
from .core.tex_utils import ParseMode


@module.cmd("tex",
            desc="Render LaTeX code.",
            aliases=[',', 'mtex', 'align', 'latex', 'texsp', 'texw', 'tikz'],
            flags=['config', 'keepsourcefor', 'color', 'colour', 'alwaysmath', 'allowother', 'name'])
async def cmd_tex(ctx, flags):
    """
    Usage``:
        {prefix}, <equations>
        {prefix}tex <code>
        {prefix}align <align block>
        {prefix}texsp <code>
        {prefix}texw <code>
        {prefix}tikz <code>
    Description:
        Compiles and displays [LaTeX](https://www.overleaf.com/learn/latex/Learn_LaTeX_in_30_minutes) document code.\
            For a quick introduction to using LaTeX, see one of the resources linked below.

        The output is extensively configurable, see `{prefix}help texconfig` \
            for more information about the possible configuration options.

        LaTeX macros and packages may also be used in this command via \
            inclusion into the *preamble*, see `{prefix}help preamble` for more information.

        If a guild or user has *latex recognition* enabled (see `{prefix}config latex` and `{prefix}help autotex`), \
            messages containing LaTeX will automatically be compiled and this command \
            is generally not required.
    Aliases::
        tex: Code is compiled in the default `document` environment.
        , or mtex: Code is rendered in math mode, in a `gather*` environment.
        align: Code is rendered in math mode, aligned in an `align*` environment.
        texsp: Same as `tex`, but ||spoiler|| the output image.
        texw: Don't pad the output (with transparent pixels) after compilation.
        tikz: Code is rendered in a `tikzpicture` environment.
    Related:
        autotex, texconfig, preamble
    LaTeX Resources:
        [Our own LaTeX cheat-sheet](https://cdn.discordapp.com/attachments/570695825186095134/570696097572585483/texit_cheatsheet_1.pdf)
        [LaTeX Mathematical symbols for undergrads (and everyone else)](http://tug.ctan.org/info/undergradmath/undergradmath.pdf)
        [Find a LaTeX symbol by drawing it on Detexify](http://detexify.kirelabs.org/classify.html)
        [Friendly introduction to mathematical LaTeX, with links](https://www.overleaf.com/learn/latex/Learn_LaTeX_in_30_minutes#Adding_math_to_LaTeX)
        [TeX Stackexchange, where every question has been asked before](https://tex.stackexchange.com/)
        [The LaTeX Support Discord server, origin of the LaTeX Support Network!](https://discord.gg/CbbUP7cDGK)
    Examples``:
        {prefix}tex This is a fraction: \\(\\frac{{1}}{{2}}\\)
        {prefix}, \\int^\\infty_0 f(x)~dx
        {prefix}align a + 1 &= 2\\\\ a &= 1
        {prefix}tikz \\draw(0,0) circle (1);
    """
    # Handle flags
    if any(flags.values()):
        return await ctx.error_reply(
            "LaTeX configuration has moved to the `texconfig` command.\n"
            "Please see `{}help texconfig` for usage.".format(ctx.best_prefix())
        )

    # Handle empty and erroneous input
    if ctx.alias == ',':
        if not ctx.args.strip(','):
            # We shouldn't respond to any number of ',' characters on their own.
            return
    elif not ctx.args:
        if ctx.alias == ',':
            # `,,` on its own might easily not be referring to us.
            return
        else:
            return await ctx.error_reply(
                "Please give me something to compile, for example "
                "```latex\n"
                "{0}tex The solutions to \\(x^2 = 1\\) are \\(x = \\pm 1\\)."
                "```"
                "See `{0}help` and `{0}help tex` for detailed usage and further examples!".format(ctx.best_prefix())
            )

    # Handle `tex help`
    if ctx.args.lower() in ['help', '--help']:
        return await ctx.error_reply("Please use `{}help tex` for command help.".format(ctx.best_prefix()))

    # TODO: Warning about \begin{document} and \documentclass
    if r"\begin{document}" in ctx.args or r"\documentclass" in ctx.args or r"\usepackage" in ctx.args:
        await ctx.error_reply(
            "I compile the code you give me by putting it into a template LaTeX document, between "
            "`\\begin{{document}}` and `\\end{{document}}` commands.\n"
            "Please don't give me code that belongs outside of there!\nSee `{prefix}help tex` for some examples "
            "of what I understand.\n\n"
            "**If you want to modify the template to add packages or your own macros, "
            "see `{prefix}help preamble`.**".format(prefix=ctx.best_prefix())
        )

    # Get latex user and guild
    lguild = LatexGuild.get(ctx.guild.id if ctx.guild else 0)
    luser = LatexUser.get(ctx.author.id)

    # Determine parse mode and flags
    flags = {}
    parse_mode = ParseMode.DOCUMENT

    lalias = ctx.alias.lower()
    if lalias in [',', 'mtex']:
        parse_mode = ParseMode.GATHER
    elif lalias == 'align':
        parse_mode = ParseMode.ALIGN
    elif lalias == 'tikz':
        parse_mode = ParseMode.TIKZ
    elif lalias == 'texsp':
        flags["spoiler"] = True
    elif lalias == "texw":
        flags["wide"] = True

    # Clean mentions
    content = ctx.clean_arg_str()

    # Parse source
    source = LatexContext.parse_content(content, parse_mode)

    if not source:
        return await ctx.error_reply(
            "Codeblocks found, but no LaTeX codeblocks!\n"
            "Please write your codeblocks as follows.\n"
            "\\`\\`\\`tex\ncode\n\\`\\`\\`"
        )

    # Create the LatexContext
    lctx = LatexContext(ctx, source, lguild, luser, **flags)

    # Make the LaTeX
    await lctx.make()

    # Keep the command alive until the latex context dies
    await lctx.lifetime()
