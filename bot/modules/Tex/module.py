from paraModule import paraModule

latex_module = paraModule(
    "LaTeX Rendering",
    description="Render LaTeX code and configure rendering options."
)
# TODO: A link on LaTeX here could work.


"""
Commands and handlers for LaTeX compilation, both manual and automatic.

Commands provided:
    texlisten:
        Toggles a user-setting for global tex recognition
    tex:
        Manually render LaTeX and configure rendering settings.

Handlers:
    tex_edit_listener:
        Listens to edited messages for automatic tex (re)compilation
    tex_listener:
        Listens to all new messages for automatic tex compilation

Initialisation:
    register_tex_listeners:
        Add all users and servers with tex listening enabled to bot objects

Bot Objects:
    user_tex_listeners: set of user id strings
    server_tex_listeners: dictionary of lists of math channel ids, indexed by server id
    latex_messages: dictionary of Contexts, indexed by message ids

User data:
    tex_listening: bool
        (app specific, user configured)
        Whether the user has global tex listening enabled
    latex_keepmsg: bool
        (app specific, user configured)
        Whether the latex source message will be deleted after compilation
    latex_colour: string
        (app specific, user configured)
        The background colour for compiled LaTeX output
    latex_alwaysmath: bool
        (app specific, user configured)
        Whether the `tex` command should render in paragraph or math mode
    latex_allowother: bool
        (app specific, user configured)
        Whether other users are allowed to use the showtex reaction on compiled output
    latex_showname: bool
        (app specific, user configured)
        Whether the user's name should be shown on the output
    latex_preamble: string
        (app independent, user configured)
        The preamble used in LaTeX compilation
    limbo-preamble: string
        (app independent, user configured)
        A preamble submitted by the user which is awaiting approval

Server data:
    maths_channels: list of channel ids
        (app specific, admin configured)
        The channels with automatic latex recognition enabled
    latex_listen_enabled: bool
        (app specific, admin configured)
        Whether automatic latex recognition is enabled at all
"""
