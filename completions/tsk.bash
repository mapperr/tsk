# shellcheck shell=bash
# Bash completion for tsk. Source this file from ~/.bashrc.
# Requires Bash 4 or newer; bash-completion is not required.

_tsk_complete() {
    local i word cur cmd candidate prefix='' namespace tool options=0 ids=0 tags=0 keys=0 value_key='' id_command=l previous files=0
    local -a words=() candidates=() list_options=() known_tags=()
    local -A seen=()
    COMPREPLY=()

    # Bash normally splits +key:value into +key, :, value. Reassemble these
    # words without changing the user's global COMP_WORDBREAKS setting.
    for ((i=0; i<=COMP_CWORD; i++)); do
        word=${COMP_WORDS[i]}
        if ((${#words[@]})) && { [[ $word == : ]] || [[ -n $word && ${COMP_WORDS[i-1]} == : ]]; }; then
            words[${#words[@]}-1]+=$word
        else
            words+=("$word")
        fi
    done
    local cword=$((${#words[@]}-1))
    cur=${words[cword]}
    tool=${words[0]}
    cmd=${words[1]-}
    previous=${words[cword-1]-}

    if ((cword == 1)); then
        candidates=(a l r s e 'done' open due t tags d dir check g h help inbox next backlog waiting unassigned projects team report issue browse import --help)
        while IFS= read -r candidate; do
            candidates+=("${candidate#"${tool##*/}-"}")
        done < <(compgen -c -- "${tool##*/}-")
    else
        case $cmd in
            a) tags=1 ;;
            l|inbox|next|backlog|waiting|unassigned|projects|team|report)
                id_command=$cmd
                ids=1; tags=1; options=1
                for ((i=2; i<cword; i++)); do
                    case ${words[i]} in
                        --all|--done) list_options=("${words[i]}") ;;
                        --) options=0; break ;;
                    esac
                done
                ((options)) && candidates+=(--all --done --body --ids --json --group-by --sort --has --without --since --until --all-time)
                ;;
            r|done) ids=1; tags=1 ;;
            open) ids=1; tags=1; list_options=(--done) ;;
            s|e|d) ids=1; tags=1; list_options=(--all) ;;
            t)
                tags=1; list_options=(--all)
                if ((cword == 2)) || { ((cword == 3)) && [[ ${words[2]} == --dry-run ]]; }; then ids=1; fi
                ;;
            due)
                if ((cword == 2)) || { ((cword == 3)) && [[ ${words[2]} == --dry-run ]]; }; then
                    candidates=(today tomorrow monday tuesday wednesday thursday friday saturday sunday -)
                else
                    ids=1; tags=1; list_options=(--all)
                fi
                ;;
            tags)
                keys=1; options=1
                for ((i=2; i<cword; i++)); do
                    case ${words[i]} in
                        --all|--done|--names) ;;
                        --) options=0 ;;
                        *) options=0; keys=0 ;;
                    esac
                done
                ((options)) && candidates+=(--all --done --names)
                ;;
            browse) ids=1; list_options=(--all); candidates+=(--print) ;;
            import) files=1 ;;
            issue)
                if ((cword == 2)); then
                    candidates=(set open import)
                else
                    case ${words[2]} in
                        open) ids=1; list_options=(--all); candidates+=(--print) ;;
                        set)
                            candidates+=(--dry-run)
                            if ((cword == 3)) || [[ $previous == --dry-run ]]; then ids=1; list_options=(--all); fi
                            ;;
                        import) files=1 ;;
                    esac
                fi
                ;;
        esac

        case $cmd in done|open|due|t|d) if ((cword == 2)); then candidates+=(--dry-run); fi ;; esac
        case $previous in
            --group-by|--has|--without) candidates=(project owner wait issue source); ids=0; tags=0; keys=1; files=0 ;;
            --sort) candidates=(id title due completed); ids=0; tags=0; keys=0; files=0 ;;
            --since|--until) candidates=(today yesterday monday); ids=0; tags=0; files=0 ;;
            --source) candidates=(auto tsk generic jira gitlab redmine); files=0 ;;
            --owner) value_key=owner; files=0 ;;
            --project|--only-project) value_key=project; files=0 ;;
            --base-url|--closed-status|--tag) files=0 ;;
        esac
        if ((files)); then
            if [[ $cur == --* ]]; then
                candidates=(--source --base-url --project --owner --tag --only-project --only-open --closed-status --dry-run)
            else
                compopt -o filenames -o default 2>/dev/null || :
                while IFS= read -r candidate; do COMPREPLY+=("$candidate"); done < <(compgen -f -- "$cur")
                return 0
            fi
        fi

        if [[ -n $cur && $cur != +* && $cur != -+* && $cur != - ]]; then tags=0; fi
        if [[ $cur == [-+]* ]]; then ids=0; fi
        if ((tags || keys)) || [[ -n $value_key ]]; then
            while IFS= read -r candidate; do
                known_tags+=("$candidate")
            done < <("$tool" tags --all --names </dev/null 2>/dev/null)
        fi
        if ((keys)); then
            for candidate in "${known_tags[@]}"; do
                [[ $candidate == *:* ]] || continue
                namespace=${candidate#+}
                candidates+=("${namespace%%:*}")
            done
        fi
        if [[ -n $value_key ]]; then
            for candidate in "${known_tags[@]}"; do
                [[ $candidate == "+$value_key:"* ]] && candidates+=("${candidate#*:}")
            done
        fi
        if ((tags)); then
            known_tags+=(+done +next +inbox +backlog +wait +due: +completed:)
            for candidate in "${known_tags[@]}"; do
                if [[ ( $cur == - || $cur == -+* ) && $cmd != a ]]; then
                    candidates+=("-$candidate")
                else
                    candidates+=("$candidate")
                fi
            done
        fi
        if ((ids)); then
            while IFS= read -r candidate; do
                if [[ $candidate =~ ^[[:space:]]*\[([^]]+)\] ]]; then
                    candidates+=("${BASH_REMATCH[1]}")
                fi
            done < <("$tool" "$id_command" "${list_options[@]}" </dev/null 2>/dev/null)
        fi
    fi

    # Readline replaces only the part after the last colon when ':' is a word
    # break, so trim the namespace from replies after matching the whole tag.
    if [[ $COMP_WORDBREAKS == *:* && $cur == *:* ]]; then
        prefix=${cur%:*}:
    fi
    for candidate in "${candidates[@]}"; do
        [[ $candidate =~ ^[-+A-Za-z0-9_.:]+$ ]] || continue
        [[ $candidate == "$cur"* ]] || continue
        candidate=${candidate#"$prefix"}
        [[ -n $candidate ]] || continue
        [[ ${seen[$candidate]+yes} ]] && continue
        seen[$candidate]=1
        COMPREPLY+=("$candidate")
    done
    if ((${#COMPREPLY[@]} == 1)) && [[ ${COMPREPLY[0]} == *: ]]; then
        compopt -o nospace 2>/dev/null || :
    fi
    return 0
}

complete -F _tsk_complete tsk
