import argparse
import os
import sys
from hashlib import md5
import shutil
import time

from itertools import zip_longest
from subprocess import Popen
from datetime import datetime
from docopt import docopt

__doc__ = """dotgit: Dotfiles management made easy.

Usage:
    dotgit ( -h | --help )
    dotgit (-l DIR) (-w DIR) [options]

Options:
  -h --help                 Show this screen.
  -l DIR --local=DIR        Local Directory [default: /home/strixx/]
  -w DIR --working=DIR      Folder to put dotfiles, example: dotgit folder [default: /home/strixx/.dotfiles/]
  -v --verbose              Print operations to screen
  -r --restore              Cleanup local and copy all files from working directory
  -s --symlink              Use symbolic links insteed of copy mode.
  --version                 Show version.

"""


def folderCheck():
    """Check if dotfilesPath tree is not empty and has correct folders"""

    if not os.path.exists(dotfilesPath + 'dotfiles'):

        print("""Directory variable empty or not found, are you sure this is the right directory?
Make sure to end Local and dotfilesPath directory path with ''/""")
        answer = input("=> Do you want to setup dotfiles in this directory? ")
        if "y" not in answer.lower():
            return False

        if verbose:
            print("Creating directory in: " + dotfilesPath + 'dotfiles')
            print("Creating directory in: " + dotfilesPath + 'dotfiles/common')
            print("Creating directory in: " +
                  dotfilesPath + 'dotfiles/' + host)
            print("------------------------------------------------\n")
        else:
            try:
                reqDirs = [dotfilesPath + "dotfiles/common",
                           dotfilesPath + "dotfiles/" + host]
                for reqdir in reqDirs:
                    os.makedirs(reqdir, exist_ok=False)
                with open(dotfilesPath + 'filelist', 'a'):
                    os.utime(dotfilesPath + 'filelist', None)

            except Exception:
                return False

    return True


def get_filelist(path, hostname=None, home=None):
    if not home:
        fullpath = "{}{}/{}".format(dotfilesPath, hostname, path)
    else:
        fullpath = "{}{}".format(userHome, path)

    if os.path.isdir(fullpath):
        _files = []
        for root, _, files in os.walk(fullpath):
            for name in files:
                _files.append(root + "/" + name)

        return _files
    else:
        return fullpath


def symlink_files(src, dest):
    """Symlink function, use src to symlink to dest"""

    if verbose:
        print("Symlink: {} | {}".format(src, dest))

    else:
        try:
            os.symlink(src, dest)
            if verbose:
                print("Making symbolic link: " + dest)

        except Exception as e:
            raise
            os.makedirs(os.path.dirname(dest))


def sync_files(localPath, workingPath):
    if verbose:
        print("Sync: {} : {}".format(workingPath, localPath))

    working_hash = hash_md5(workingPath)
    local_hash = hash_md5(localPath)

    if restore and working_hash not in local_hash:
        os.remove(localPath)
        shutil.copy2(workingPath, localPath)
    if not restore and working_hash not in local_hash:
        os.remove(workingPath)
        shutil.copy2(localPath, workingPath)

    return


def restore_files(localPath, workingPath, hostname):

    if symlink:
        symlink_files(workingPath, localPath)
        return

    if verbose:
        print("Restoring: {} : {}".format(workingPath, localPath))

    else:
        try:
            shutil.copy2(workingPath, localPath)
        except IOError as e:
            # try creating parent directories
            os.makedirs(os.path.dirname(localPath), exist_ok=True)
            shutil.copy2(workingPath, localPath)


def add_files(localPath, workingPath):

    if verbose:
        print("Adding: {} : {}".format(localPath, workingPath))

    else:
        try:
            shutil.copy2(localPath, workingPath)

        except IOError as e:
            os.makedirs(os.path.dirname(workingPath), exist_ok=True)
            try:
                shutil.copy2(localPath, workingPath)
            except:
                pass

        if symlink:
            os.remove(localPath)
            symlink_files(workingPath, localPath)


def hard_copy(localPath, workingPath, hostname="common"):
    if restore:
        try:
            localPath = workingPath.replace(
                dotfilesPath + "dotfiles/" + hostname + "/", userHome)
            exists_gPath = os.path.exists(workingPath)
            exists_lPath = os.path.exists(localPath)
        except Exception:
            return
    else:
        try:
            workingPath = localPath.replace(
                userHome, dotfilesPath + "dotfiles/" + hostname + "/")
            exists_lPath = os.path.exists(localPath)
            exists_gPath = os.path.exists(workingPath)
        except AttributeError:
            workingPath = localPath.replace(
                userHome, dotfilesPath + "dotfiles/" + hostname + "/")
            exists_lPath = os.path.exists(localPath)
            exists_gPath = os.path.exists(workingPath)

    if exists_lPath and not exists_gPath:
        add_files(localPath, workingPath)
        return

    # if exists_lPath and exists_gPath and not symlink:
    #     sync_files(workingPath, localPath)
    #     return

    # if exists_lPath and exists_gPath and symlink:
    #     symlink_files(workingPath, localPath)
    #     return

    if restore and not exists_lPath and exists_gPath:
        restore_files(localPath, workingPath, hostname)
        return

    if not restore and not exists_lPath and exists_gPath:
        os.remove(workingPath)
        return


def readFilelist():
    """Get filelist from filelist file"""

    try:
        with open("filelist", mode='r') as f:
            for __ in f.readlines():
                filePath = __.replace('\n', '')
                if filePath:
                    if ':' not in filePath:
                        gitPath = get_filelist(filePath, "dotfiles/common")
                        localPath = get_filelist(filePath, home=1)

                        if type(gitPath) == list or type(localPath) == list:
                            for localPath, gitPath in zip_longest(localPath, gitPath):
                                hard_copy(localPath, gitPath)
                        else:
                            hard_copy(localPath, gitPath)

                    else:
                        filePath, hostname = filePath.split(':')
                        if hostname in host:
                            gitPath = get_filelist(
                                filePath, "dotfiles/" + hostname)
                            localPath = get_filelist(filePath, home=1)
                            if type(gitPath) == list or type(localPath) == list:
                                for localPath, gitPath in zip_longest(localPath, gitPath):
                                    hard_copy(localPath, gitPath, hostname)
                            else:
                                hard_copy(localPath, gitPath, hostname)

    except FileNotFoundError:
        raise
        print("File not found: {}filelist".format(dotfilesPath))


def hash_md5(fname):
    hash_md5 = md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


if __name__ == "__main__":
    args = docopt(__doc__, version="dotgit 0.1 alpha")

    userHome = args['--local']
    dotfilesPath = args['--working']
    verbose = args['--verbose']
    restore = args['--restore']
    symlink = args['--symlink']
    host = os.uname()[1]

    print("------------------------------------------------")
    print("Local  : '{}'".format(userHome))
    print("Working: '{}'".format(dotfilesPath))
    print("Verbose: " + str(verbose))
    print("Restore: " + str(restore))
    print("Symlink: " + str(symlink))
    print("Host   : " + host)
    print("------------------------------------------------")

    if folderCheck():
        answer = input("=> Do you want to contiunue? ")
        if "y" in answer.lower():
            readFilelist()
