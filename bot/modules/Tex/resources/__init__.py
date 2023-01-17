import os


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Load default preamble from file
with open(os.path.join(__location__, "default_preamble.tex"), 'r') as preamble:
    default_preamble = preamble.read()

# Load list of whitelisted packages from file
with open(os.path.join(__location__, "package_whitelist.txt"), 'r') as pw:
    whitelisted_packages = [line.strip() for line in pw]

# Store the path to the failed image
failed_image_path = os.path.join(__location__, "failed.png")

# Store the path to the latex compile script
compile_script_path = os.path.join(__location__, "texcompile.sh")
