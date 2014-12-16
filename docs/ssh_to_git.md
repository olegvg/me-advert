Gaining r/o access to (Bitbucket) git from production server
============================================================


Assume that running user is 'olegvg'.

Under the `olegvg` user:

1. Create `~olegvg/.bash_profile` and fill with following code, which starts ssh-agent at login and adds some handy aliases:

        # File: ~/.bash_profile

        # source ~/.profile, if available
        if [[ -r ~/.profile ]]; then
          . ~/.profile
        fi

        # start agent and set environment variables, if needed
        agent_started=0
        if ! env | grep -q SSH_AGENT_PID >/dev/null; then
          echo "Starting ssh agent"
          eval $(ssh-agent -s)
          agent_started=1
        fi

        # ssh become a function, adding identity to agent when needed
        ssh() {
          if ! ssh-add -l >/dev/null 2>-; then
            ssh-add ~/.ssh/id_rsa
          fi
          /usr/bin/ssh "$@"
        }
        export -f ssh

        # another example: git
        git() {
          if ! ssh-add -l >/dev/null 2>-; then
            ssh-add ~/.ssh/id_rsa
          fi
          /usr/bin/git "$@"
        }
        export -f git

2. Add following code to the end of `~olegvg/.bash_logout`:

        # killing ssh-agent on logout
        if ((agent_started)); then
          echo "Killing ssh agent"
          ssh-agent -k
        fi

3. Create ssh key pair:

        ssh-keygen -f ~olegvg/.ssh/id_rsa

4. Put contents of just generated `~olegvg/.ssh/id_rsa.pub` to Bitbucket under repository's deployment keys (<https://bitbucket.org/olegvg/me-advert/admin/deploy-keys>)

