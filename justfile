@_default:
    just -f {{justfile()}} --list

doc:
    #!/bin/sh
    for k in $(env | grep '^TSK_' | cut -d'=' -f1); do unset $k; done
    TSK_USAGE="$(./tsk h)" \
        envsubst '$TSK_USAGE' <README.tpl.md >README.md
    sed -i "s@$HOME@\$HOME@" README.md
