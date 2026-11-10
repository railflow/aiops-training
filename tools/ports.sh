#!/usr/bin/env bash
# Shared helper for tools/kind: find free host ports and remember them.
# Source it, do not run it:   . "$(dirname "$SELF")/ports.sh"
# It installs nothing and changes nothing outside .logs/.
#
# A port counts as busy when something listens on it (lsof, else nc, else bash /dev/tcp), when a running docker
# container publishes it (docker ps), or when this run already picked it for something else.
#
# Callers may redefine ports_note and ports_fail after sourcing to use their own styling.
#
# Test seams: PORTS_ROOT (repo root, default: parent of scripts/), PORTS_LOGS (default: $PORTS_ROOT/.logs).

PORTS_ROOT="${PORTS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PORTS_LOGS="${PORTS_LOGS:-$PORTS_ROOT/.logs}"
PORTS_ENV_FILE="${PORTS_ENV_FILE:-$PORTS_LOGS/ports.env}"
PORTS_RESERVED=" "
PORT_BUSY_WHO=""
PORTS_DOCKER_LOADED=0
PORTS_DOCKER_LINES=""

ports_note() { printf '%s\n' "$*" >&2; }
ports_fail() { printf '%s\n' "$*" >&2; }

# ports_strip_ansi: remove colour codes from stdin.
ports_strip_ansi() { sed $'s/\033\\[[0-9;]*[A-Za-z]//g'; }

# port_busy PORT: return 0 if busy and set PORT_BUSY_WHO to a short description, else return 1.
port_busy() {
  local p="$1" who="" line
  PORT_BUSY_WHO=""
  if command -v lsof >/dev/null 2>&1; then
    line="$(lsof -nP -iTCP:"$p" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1 " (pid " $2 ")"}' || true)"
    [[ -z "$line" ]] || who="$line"
  elif command -v nc >/dev/null 2>&1; then
    if nc -z 127.0.0.1 "$p" >/dev/null 2>&1; then who="another program"; fi
  elif (exec 3<> "/dev/tcp/127.0.0.1/$p") 2>/dev/null; then
    who="another program"
  fi
  if [[ -z "$who" ]] && command -v docker >/dev/null 2>&1; then
    if ((!PORTS_DOCKER_LOADED)); then
      PORTS_DOCKER_LINES="$(docker ps --format $'{{.Names}}\t{{.Ports}}' 2>/dev/null || true)"
      PORTS_DOCKER_LOADED=1
    fi
    line="$(printf '%s\n' "$PORTS_DOCKER_LINES" | grep -E ":${p}->" | head -n 1 | cut -f1 || true)"
    [[ -z "$line" ]] || who="docker container ${line}"
  fi
  if [[ -z "$who" && "$PORTS_RESERVED" == *" $p "* ]]; then
    who="another port picked in this run"
  fi
  [[ -n "$who" ]] || return 1
  PORT_BUSY_WHO="$who"
  return 0
}

# pick_port VAR LABEL DEFAULT [EXPLICIT] [MAX_STEPS]
# Sets VAR to a free port. With EXPLICIT: use exactly that port or fail (return 1) if it is busy.
# Without: DEFAULT if free, else walk upward (up to MAX_STEPS, default 50) and say why.
pick_port() {
  local var="$1" label="$2" def="$3" explicit="${4:-}" max="${5:-50}" p i first_who="" first_busy=""
  if [[ -n "$explicit" ]]; then
    if [[ ! "$explicit" =~ ^[0-9]+$ ]] || ((explicit < 1 || explicit > 65535)); then
      ports_fail "${label}: '${explicit}' is not a valid port number."
      return 1
    fi
    if port_busy "$explicit"; then
      ports_fail "${label}: the port you asked for, ${explicit}, is busy (used by ${PORT_BUSY_WHO}). Free it or choose another."
      return 1
    fi
    printf -v "$var" '%s' "$explicit"
    PORTS_RESERVED="${PORTS_RESERVED}${explicit} "
    return 0
  fi
  for ((i = 0; i <= max; i++)); do
    p=$((def + i))
    ((p <= 65535)) || break
    if port_busy "$p"; then
      if [[ -z "$first_busy" ]]; then first_busy="$p"; first_who="$PORT_BUSY_WHO"; fi
      continue
    fi
    printf -v "$var" '%s' "$p"
    PORTS_RESERVED="${PORTS_RESERVED}${p} "
    if [[ -n "$first_busy" ]]; then
      ports_note "${label}: ${first_busy} is busy (used by ${first_who}) -> using ${p}"
    fi
    return 0
  done
  ports_fail "${label}: no free port found from ${def} to $((def + max)). Free one, or set it explicitly."
  return 1
}

# ports_env_set KEY VALUE: create or update KEY=VALUE in .logs/ports.env (gitignored).
ports_env_set() {
  local k="$1" v="$2" f="$PORTS_ENV_FILE"
  mkdir -p "$(dirname "$f")"
  [[ -f "$f" ]] || printf '# Host ports chosen by tools/kind. Written automatically; not committed.\n# Use them in a shell with:  . .logs/ports.env\n' > "$f"
  { grep -v "^${k}=" "$f" || true; } > "$f.tmp"
  printf '%s=%s\n' "$k" "$v" >> "$f.tmp"
  mv "$f.tmp" "$f"
}

# ports_env_get KEY: print the value, if any.
ports_env_get() {
  [[ -r "$PORTS_ENV_FILE" ]] || return 1
  local line
  line="$(grep "^${1}=" "$PORTS_ENV_FILE" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 1
  printf '%s\n' "${line#*=}"
}
