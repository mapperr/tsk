@_default:
    just -f {{justfile()}} --list

doc:
    #!/bin/sh
    unset TSK_DIR
    unset TSK_CATCMD
    unset TSK_DEBUG
    TSK_USAGE="$(./tsk h)" \
        envsubst '$TSK_USAGE' <README.tpl.md >README.md
    sed -i "s@$HOME@\$HOME@" README.md
