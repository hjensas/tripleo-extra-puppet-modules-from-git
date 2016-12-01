# TripleO - Extra Puppet Modules from Git Repo

This OpenStack HEAT template can be used with TripleO to install additional
puppet modules from git repositories during the pre-deploy stage.

Once the modules are installed they can be included as part of the TripleO
deployment as ExtraConfig like this:


### Example: NodeExtraConfig environment file
```
resource_registry:
   OS::TripleO::NodeExtraConfig: /home/stack/templates/extraconfig/pre_deploy/extra-puppet-modules-from-git/extra-puppet-modules-from-git.yaml

parameter_defaults:
  ExtraPuppetModulesFromGit:
    - server: gitserver.example.com
      protocol: git
      ssh-user: username
      ssh-key: |
        -----BEGIN RSA PRIVATE KEY-----
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        -----END RSA PRIVATE KEY-----
      repos:
        - repo: /path/to/puppet-modules.git
          modules:
            - foo-bar
            - foo-baz
        - repo: /path/to/my-modules.git
          modules:
            - corp-idm
            - corp-sudo
    - server: github.com
      protocol: https
      https-user: user
      https-secret: <password or auth-token>
      repos:
        - repo: user/puppet-auditd.git
        - repo: user/sssd.git
```


### Example: Extraconfig Environment file
```
parameter_defaults:
  #
  # All nodes, ExtraConfig
  #
  ExtraConfig:
    compute_classes:
      - ::vim
      - ::motd
      - ::rsyslog::client
    controller_classes:
      - ::vim
      - ::motd
      - ::rsyslog::client

    rsyslog::client::spool_size: 2g
    rsyslog::client::remote_servers:
      - host: logs.foo.example.com
        port: 55514
        protocol: udp
      - host: logs.bar.example.com
        port: 555
        pattern: '*.log'
        protocol: tcp
        format: RFC3164fmt
```
