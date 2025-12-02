@_default:
    just -f {{justfile()}} --list

doc:
    #!/bin/sh
    TSK_USAGE="$(./tsk h)" \
        envsubst '$TSK_USAGE' <README.tpl.md >README.md
