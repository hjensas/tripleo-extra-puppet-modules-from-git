#!/bin/python
from subprocess import PIPE, Popen
import json
import yaml
import os
import stat
import re
from time import strftime

MODULE_PATH = '/etc/puppet/modules'
MODULE_STAGE_DIR = '/var/tmp/modules_stage' + strftime("-%d%m%Y-%H%M")
KEYS_DIR = '/var/tmp/keys'
WRAPPERS_DIR = '/var/tmp/wrappers'
INPUT_ENV_VAR = 'EXTRA_PUPPET_MODULES_GIT'


if not os.path.exists(MODULE_PATH):
  os.makedirs(MODULE_PATH)
if not os.path.exists(MODULE_STAGE_DIR):
  os.makedirs(MODULE_STAGE_DIR)
if not os.path.exists(KEYS_DIR):
  os.makedirs(KEYS_DIR)
if not os.path.exists(WRAPPERS_DIR):
  os.makedirs(WRAPPERS_DIR)

                         
### Create loader for the Ruby object in puppet yaml
def construct_ruby_object(loader, suffix, node):
  return loader.construct_yaml_map(node)

def construct_ruby_sym(loader, node):
  return loader.construct_yaml_str(node)

yaml.add_multi_constructor(u'!ruby/object:', construct_ruby_object)
yaml.add_constructor(u'!ruby/sym', construct_ruby_sym)
###

def get_installed_modules(modulepath):
  #
  # Get list of installed modules
  #
  installed_modules = []
  data = yaml.load(Popen(( 'puppet', 'module', 'list',
                           '--modulepath', modulepath,
                           '--render-as', 'yaml'),
                           stdout=PIPE).communicate()[0])
  for module in data['modules_by_path'][modulepath]:
    installed_modules.append(module.get('name'))
  return installed_modules

def create_key_file(server, keysDir, sshKey):
  # 
  # Create ssh-priv-key file, close, set perms, add key
  #
  ssh_key_file = keysDir + '/' + server + '.ssh-key'
  file = open(ssh_key_file, 'w')
  file.close()
  os.chmod(ssh_key_file, 0600)
  file = open(ssh_key_file, 'w')
  file.write(sshKey)
  file.close()
  return ssh_key_file

def create_git_wrapper(server, wrapperDir, keysDir):
  # 
  # Create GIT_SSH wrapper file, close, set perms, add content
  #
  git_wrapper_file = wrapperDir + '/' + server + '.wrapper'
  file = open(git_wrapper_file, 'w')
  file.close()
  os.chmod(git_wrapper_file, 0700)
  file = open(git_wrapper_file, 'w')
  file.write('#!/bin/bash\n\n'
              + 'ssh -o StrictHostKeyChecking=no -i ' + keysDir + '/'
              + server + '.ssh-key $1 $2\n')
  file.close()
  return git_wrapper_file

def create_git_config(server, keysDir, credentialsFile):
  #
  # Set up a config file using the credentials store
  #
  git_config_file = keysDir + '/' + '.gitconfig'
  ps = Popen([ 'git', 'config', '--file', git_config_file,
               'credential.helper', 'store --file=' + credentialsFile ])
  ps.communicate()
  return git_config_file


def create_git_credentials(server, gitUrl, httpUser, httpSecret, keysDir):
  #
  # Create git credential store file, close, set perms, add credentials
  #
  git_credentials_file = keysDir + '/' + server + '.gitcredentials'
  file = open(git_credentials_file, 'w')
  file.close()
  os.chmod(git_credentials_file, 0600)
  file = open(git_credentials_file, 'w')
  file.write('https://' + httpUser + ':' + httpSecret + '@' + server)
  file.close()
  return git_credentials_file

def get_module_name(stageDir, repo, module):
  #
  # Get module name from metadata.json
  #
  if module:
    file = open(stageDir + '/' + repo + '/'
                + module + '/' + 'metadata.json', 'r')
  if not module:
    file = open(stageDir + '/' + repo + '/' + 'metadata.json', 'r')
  module_name = json.load(file).get('name')
  file.close()
  return module_name

def puppet_module_uninstall(module, module_path):
  #
  # Uninstall a puppet module
  #
  ps = Popen([ 'puppet', 'module', 'uninstall', '--force',
               '--modulepath', MODULE_PATH, module ])
  ps.communicate()
  return None

def puppet_module_build(stageDir, repo, module):
  #
  # Build puppet module distribution package 
  #
  if not module:
    ps = Popen([ 'puppet', 'module', 'build',
                 stageDir + '/' + repo ], stdout=PIPE)
  else:
    ps = Popen([ 'puppet', 'module', 'build',
                 stageDir + '/' + repo + '/' + module ], stdout=PIPE)
  out, err = ps.communicate()
  module_package = re.sub(r'.*\sModule built:\s', '', out).strip()
  return module_package

def puppet_module_install(modulePackage, modulePath):
  #
  # Install puppet module
  #
  ps = Popen([ 'puppet', 'module', 'install', '--ignore-dependencies', 
               '--target-dir', modulePath, modulePackage ])
  ps.communicate()
  return None

def git_clone_ssh(wrapperFile, repoUrl, repoName, stageDir):
  #
  # Clone a git repositry using git+ssh protocol
  #
  ps = Popen([ 'env', 'GIT_SSH=' + wrapperFile, 'git', 'clone', repoUrl,
               stageDir + '/' + repoName.split('/').pop() ])
  ps.communicate()
  return None

def git_clone_https(repoUrl, repoName, stageDir, keysDir):
  #
  # Clone a git repository using git+https protocol
  #
  # Setting HOME is the only way I found to get git to use the config file
  ps = Popen([ 'env', 'GIT_SSL_NO_VERIFY=true', 'HOME=' + keysDir,
               'git', 'clone', repoUrl,
               stageDir + '/' + repoName.split('/').pop() ])
  ps.communicate()
  return None

#
# Main
#
indata = yaml.safe_load(os.environ.get(INPUT_ENV_VAR))
installed_modules = get_installed_modules(MODULE_PATH)

for git in indata:

  if git.get('protocol') == 'git':
    git_url = git.get('ssh-user') + '@' + git.get('server') + ':'
    ssh_key_file = create_key_file(git.get('server'),
                                   KEYS_DIR, git.get('ssh-key'))
    git_wrapper_file = create_git_wrapper(git.get('server'),
                                          WRAPPERS_DIR, KEYS_DIR)

  if git.get('protocol') == 'https':
    git_url = 'https://' + git.get('server') + '/'
    git_credentials_file = create_git_credentials(git.get('server'),
                                                  git_url, 
                                                  git.get('https-user'),
                                                  git.get('https-secret'),
                                                  KEYS_DIR)
    git_config_file = create_git_config(git.get('server'), KEYS_DIR,
                                        git_credentials_file)

  for repo in git.get('repos'):
    # Git repos in input use full path to repo,
    #  e.g /var/git/repository.git 
    #  strip of path to get repo name only.
    repo_name = repo.get('repo').split('/').pop()
    repo_url = git_url + repo.get('repo')
    
    # Clone the git repository
    if git.get('protocol') == 'git':
      git_clone_ssh(git_wrapper_file, repo_url,
                    repo.get('repo'), MODULE_STAGE_DIR)
    elif git.get('protocol') == 'https':
      git_clone_https(repo_url, repo.get('repo'),
                      MODULE_STAGE_DIR, KEYS_DIR)
    else:
      print "Unknown protocol: " + git.get('protocol')
      quit()

    if repo.has_key('modules'):
      # 
      # Git repository with multiple puppet modules
      #
      for module in repo.get('modules'):
        module_name = get_module_name(MODULE_STAGE_DIR, repo_name, module)
        if module_name.split('-').pop() in installed_modules:
          puppet_module_uninstall(module_name, MODULE_PATH)
        module_pkg = puppet_module_build(MODULE_STAGE_DIR, repo_name, module)
        puppet_module_install(module_pkg, MODULE_PATH)

    else:
      # 
      # Git repository with one puppet module
      #
      module_name = get_module_name(MODULE_STAGE_DIR, repo_name, '')
      if module_name.split('-').pop() in installed_modules:
        puppet_module_uninstall(module_name, MODULE_PATH)
      module_pkg = puppet_module_build(MODULE_STAGE_DIR, repo_name, '')
      puppet_module_install(module_pkg, MODULE_PATH)

