#!/usr/bin/env python3

import argparse
import logging
import shutil
import sys
import os
import subprocess

import pdb

# Editor that we are using
EDITOR = os.environ.get('EDITOR', 'vim')

# Default folder with encrypted quartus data
DEF_RTL_OUT_F       = "rtl_quartus"
DEF_RTL_OUT_TOOL    = "quartus"
SIM_TOOL_CHOICES    = ["aldec","cadance","mentor","synopsis"]
ENC_TOOL            = "encrypt_1735"
# Mapping between extension and argument value
ENC_FILE_TYPE_MAP   = {
    ".vhd"   : "vhdl",
    ".vhdl"  : "vhdl",
    ".v"     : "verilog",
    ".sv"    : "systemverilog"
}
# Files that shouldn't be encrypted - basically simulation folder and wrapper
NOT_ENC_FILES = [
    "sim",
    "wrapper",
    "test"
]

# Dictionary with results for the next turn
RES_DIC= {}

def parse_args():
    parser = argparse.ArgumentParser(description="This program is used for encryption of sources for Quartus and simulation tools. "
                                        "It takes the <src> and <dst> and does the recursive file encryption.")
    parser.add_argument("src", type=str,
            help="source folder that we want to encrypt")
    parser.add_argument("dst", type=str,
            help="destination folder with encrypted data")
    parser.add_argument("-q", "--quartus", action="store_true",
            help="Generate folder with encrypted data")
    parser.add_argument("-a","--rtl-folder", action="store", default=DEF_RTL_OUT_F,
            help=f"Output folder with encrypted RTL sources (default is {DEF_RTL_OUT_F}) ")
    parser.add_argument("-s","--sim", nargs="+", type=str, choices=SIM_TOOL_CHOICES, default=[],
            help="Generate encrypted simulation sources. User can pass multiple simulators. "
            "Simulation sources are not enabled by default. Encrypted sources are passed to <simulator>_rtl folder.")
    parser.add_argument("-o","--overwrite",action="store_true",
            help="Overwrite the output folder.")
    parser.add_argument("-d","--debug", action="store_true",
            help="Enable debug log level.")
    parser.add_argument("-n","--not-encrypted", default=NOT_ENC_FILES, nargs="+",
            help=f"The list of patterns where user will be asked for encryption (defaults are {NOT_ENC_FILES})")
    
    return parser.parse_args()

def check_tools():
    """
    Return true if all tools are available
    """
    def _tcheck(tool):
        if shutil.which(tool) is None:
            logging.error(f"Tool {tool} is not available!")
            False
        else:
            logging.debug(f"Tool {tool} is available! ")
            return True
    ###################
    logging.debug("Checking all required tools ...")
    tools = [
        _tcheck(ENC_TOOL)
    ]
    return all(tools)

def get_encrypt_cmd(spath, fpath, eformat):
    """
    Prepare the encryption command for ENC_TOOL

    Parameters:
        - spath - source file
        - fpaht - destination file
        - tool name
    """
    ret_cmd = [ENC_TOOL]
    ret_cmd.append(spath)
    # Setup the language based on the extension
    ext = get_ext(spath)
    if ext not in ENC_FILE_TYPE_MAP:
        raise ValueError(f"Cannot encrypt the file {spath}")
    ret_cmd.append(f"-language={ENC_FILE_TYPE_MAP[ext]}")
    # Grab the tool
    if eformat is DEF_RTL_OUT_TOOL:
        ret_cmd.append("--quartus")
    else:
        ret_cmd.append(f"--simulation={eformat}")
    # Define the output file and input file
    ret_cmd.append(f"--of={fpath}")
 
    return ret_cmd

def encrypt_file(spath, dpath, force, eformat):
    """
    Encrypt the file.

    Parameters:
        - spath     - source path folder
        - dpath     - destination path folder
        - force     - overwrite the output file
        - eformat   - target encryption tool
    """
    try:
        logging.info(f"Encrypting file {spath} -> {dpath}")
        logging.debug(f"\t * Override = {force}, tool = {eformat}")
        cmd = get_encrypt_cmd(spath, dpath, eformat)
        if os.path.exists(dpath) and force:
            os.remove(dpath)

        args = {
            "args"  : cmd,
            "stdin" : None,
            "stdout": None,
            "stderr": None
        }

        if logging.root.level != logging.DEBUG:
            args["stdout"] = subprocess.DEVNULL
            args["stderr"] = subprocess.DEVNULL

        logging.debug(f"Executing the encryption command: {cmd} ")
        process = subprocess.Popen(**args)
        process.communicate()
 
    except Exception as e:
        logging.error(f"Error during the file {spath} encryption!")
        logging.error(str(e))

def get_ext(path):
    splt = os.path.splitext(path)
    logging.debug(f"Split path: {splt}")
    return splt[1]

def is_rtl_file(path):
    """
    Returns true if the file is an RTL file (based on extension)
    """
    ext = get_ext(path)
    if (ext is None) or (ext not in ENC_FILE_TYPE_MAP):
        logging.debug(f"File {path} is not the RTL file.")
        return False
    else:
        logging.debug(f"File {path} is the RTL file.")
        return True

def do_encrypt(spath, epatterns):
    """
    This function checks if the spath contains a given substring. It will ask a user
    for input if yes.
    """
    # Check if we already know the resulf for given file
    global RES_DIC
    if spath in RES_DIC:
        answer   = RES_DIC[spath]
        answer_s = "Y" if answer else "N"
        logging.info(f"Using previous answer {answer_s} for file {spath}")
        return answer
    
    for e in epatterns:
        if not e in spath:
            logging.debug(f"File {spath} doesn't contain the pattern {e}.")
            continue
        else:
            while True:
                answer = input(f"Do you want to encrypt the file {spath}? (y/n/e)   ").lower()
                if answer not in ["y","n","e"]:
                    print("Unknown answer, select again")
                    continue
                elif answer == "e":
                    subprocess.call([EDITOR, spath])
                    continue
                else:
                    res = answer == "y"
                    RES_DIC[spath] = res
                    return res
    return True

def process_dir_lvl(spath, dpath, force, eformat, epatterns):
    """
    Process one level of the hierarchy for the encryption.

    Parameters:
        - spath     - source path folder
        - dpath     - destination path folder
        - force     - overwrite the output file
        - eformat   - target encryption tool
        - epatterns - list of patterns that will searched as substrings and possibly not encrypted
    """
    def _pure_copy(src,dst):
        logging.warning(f"No encryption executed on the: {src}")
        shutil.copy(src, dst)

    ####################################
    if not os.path.exists(dpath):
        os.mkdir(dpath)
        logging.debug(f"Folder created: {dpath}")
    # Iterate over files in the folder and do the encryption or recursive processing
    for item in os.listdir(spath):
        ns_path = os.path.join(spath, item)
        nd_path  = os.path.join(dpath, item)

        if os.path.isdir(ns_path):
            process_dir_lvl(ns_path, nd_path, force, eformat, epatterns)
        elif os.path.isfile(ns_path):
            if is_rtl_file(ns_path) and do_encrypt(ns_path, epatterns):
                encrypt_file(ns_path, nd_path, force, eformat)
            else:
                _pure_copy(ns_path, nd_path)
        else:
            _pure_copy(ns_path, nd_path)

def print_box(msg):
    ret = "\n"
    ret += "******************************************************************\n"
    ret += f"* {msg} \n"
    ret += "******************************************************************\n"
    return ret


def main(args):
    # Setup logging
    log_lvl = logging.INFO
    if args.debug:
        log_lvl = logging.DEBUG
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_lvl)

    # Check if we are generating something (simulation or rtl)
    logging.debug(f"Passed arguments: {args}")
    if len(args.sim) == 0 and args.quartus == False:
        logging.error("Simulation or Quartus encryption should be selected!")
        sys.exit(1)

    # Create the output folder if it doesn't exists
    check_tools()
    if not os.path.exists(args.dst):
        os.mkdir(args.dst)
        logging.debug(f"Creating output folder: {args.dst}")

    # Iterate over the source directory structure and
    if args.quartus:
        logging.info(print_box("Encrypting sources for Quartus ..."))
        dst_dir = os.path.join(args.dst, args.rtl_folder)
        process_dir_lvl(args.src, dst_dir, args.overwrite, DEF_RTL_OUT_TOOL, args.not_encrypted)

    for st in args.sim:
        logging.info(print_box(f"Encrypting simulation sources (tool {st})"))
        dst_dir = os.path.join(args.dst, f"rtl_{st}")
        process_dir_lvl(args.src, dst_dir, args.overwrite, st, args.not_encrypted)

if __name__ == "__main__":
    args = parse_args()
    main(args)
