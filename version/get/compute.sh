#!/usr/bin/env bash

set -euo pipefail

: "${GITHUB_OUTPUT:?GITHUB_OUTPUT must be set}"
: "${DEFAULT_VERSION:?DEFAULT_VERSION must be set}"
: "${TAG_PREFIX:?TAG_PREFIX must be set}"

is_semver() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

plain_version() {
  local value="$1"
  local candidate

  if is_semver "${value}"; then
    printf '%s' "${value}"
    return
  fi

  if [[ "${value}" == "${TAG_PREFIX}"* ]]; then
    candidate="${value#"${TAG_PREFIX}"}"
    if is_semver "${candidate}"; then
      printf '%s' "${candidate}"
      return
    fi
  fi

  return 1
}

tag_exists() {
  git show-ref --verify --quiet "refs/tags/$1"
}

regex_escape() {
  local value="$1"
  local escaped=""
  local char
  local i

  for ((i = 0; i < ${#value}; i++)); do
    char="${value:i:1}"
    case "${char}" in
      "\\"|"."|"^"|"$"|"*"|"+"|"?"|"("|")"|"{"|"}"|"|"|"["|"]")
        escaped+="\\${char}"
        ;;
      *)
        escaped+="${char}"
        ;;
    esac
  done

  printf '%s' "${escaped}"
}

if ! git check-ref-format "refs/tags/${TAG_PREFIX}0.0.0" >/dev/null 2>&1; then
  echo "::error::tag_prefix ('${TAG_PREFIX}') cannot form a valid Git tag."
  exit 1
fi

if ! DEFAULT_PLAIN="$(plain_version "${DEFAULT_VERSION}")"; then
  echo "::error::default_version ('${DEFAULT_VERSION}') must be MAJOR.MINOR.PATCH or ${TAG_PREFIX}MAJOR.MINOR.PATCH."
  exit 1
fi
DEFAULT_TAG="${TAG_PREFIX}${DEFAULT_PLAIN}"

FORCED_PLAIN=""
if [[ -n "${FORCE_NEXT_VERSION:-}" ]]; then
  if ! FORCED_PLAIN="$(plain_version "${FORCE_NEXT_VERSION}")"; then
    echo "::error::FORCE_NEXT_VERSION ('${FORCE_NEXT_VERSION}') must be MAJOR.MINOR.PATCH or ${TAG_PREFIX}MAJOR.MINOR.PATCH."
    exit 1
  fi

  FORCED_TAG="${TAG_PREFIX}${FORCED_PLAIN}"
  if tag_exists "${FORCED_TAG}"; then
    echo "::error::FORCE_NEXT_VERSION (${FORCED_TAG}) tag already exists. Remove the tag or choose a different version."
    exit 1
  fi
fi

STREAM_TAGS=()
while IFS= read -r tag; do
  candidate="${tag#"${TAG_PREFIX}"}"
  if [[ "${tag}" == "${TAG_PREFIX}${candidate}" ]] && is_semver "${candidate}"; then
    STREAM_TAGS+=("${tag}")
  fi
done < <(git tag --list --merged HEAD)

HAS_TAGS="false"
if [[ ${#STREAM_TAGS[@]} -gt 0 ]]; then
  MATCH_ARGS=()
  for tag in "${STREAM_TAGS[@]}"; do
    MATCH_ARGS+=(--match "${tag}")
  done
  CURRENT_TAG="$(git describe --tags --abbrev=0 "${MATCH_ARGS[@]}")"
  HAS_TAGS="true"
else
  CURRENT_TAG="${DEFAULT_TAG}"
fi
CURRENT_PLAIN="${CURRENT_TAG#"${TAG_PREFIX}"}"

if [[ -n "${FORCED_PLAIN}" ]]; then
  NEXT_PLAIN="${FORCED_PLAIN}"
else
  TAG_REGEX="^$(regex_escape "${TAG_PREFIX}")[0-9]+\\.[0-9]+\\.[0-9]+$"
  CLIFF_BIN="${GIT_CLIFF_BIN:-git-cliff}"
  NEXT_RAW="$("${CLIFF_BIN}" "${CURRENT_TAG}..HEAD" \
    --bumped-version \
    --offline \
    --tag-pattern "${TAG_REGEX}" 2>/dev/null || true)"

  if NEXT_PLAIN="$(plain_version "${NEXT_RAW}")"; then
    :
  else
    if [[ -n "${NEXT_RAW}" ]]; then
      echo "::warning::git-cliff returned '${NEXT_RAW}', which does not match release stream '${TAG_PREFIX}'; falling back for ${CURRENT_TAG}."
    fi
    NEXT_PLAIN=""
  fi

  if [[ -z "${NEXT_PLAIN}" ]]; then
    if [[ "${HAS_TAGS}" == "true" ]]; then
      SVU_BIN="${SVU_BIN:-svu}"
      SVU_RAW="$("${SVU_BIN}" next \
        --always \
        --tag.prefix "${TAG_PREFIX}" \
        --tag.pattern "${CURRENT_TAG}" 2>/dev/null || true)"

      if ! NEXT_PLAIN="$(plain_version "${SVU_RAW}")"; then
        echo "::error::git-cliff could not determine a version and svu returned '${SVU_RAW:-no version}' for release stream '${TAG_PREFIX}'."
        exit 1
      fi
    else
      NEXT_PLAIN="${DEFAULT_PLAIN}"
    fi
  fi
fi

NEXT_TAG="${TAG_PREFIX}${NEXT_PLAIN}"

if [[ "${FAIL_ON_DEFAULT:-false}" == "true" && "${NEXT_PLAIN}" == "${DEFAULT_PLAIN}" ]]; then
  if [[ "${HAS_TAGS}" == "true" ]]; then
    echo "::error::Computed next version is the default (${DEFAULT_TAG}), but the repository already has tags in the '${TAG_PREFIX}' stream (current: ${CURRENT_TAG}). Check that commits follow Conventional Commits format."
    exit 1
  fi
  if tag_exists "${DEFAULT_TAG}"; then
    echo "::error::Computed next version is the default (${DEFAULT_TAG}), but that tag already exists. Check that fetch-depth: 0 is set and commits follow Conventional Commits format."
    exit 1
  fi
fi

if [[ "${FAIL_ON_SAME_VERSION:-true}" == "true" && "${NEXT_PLAIN}" == "${CURRENT_PLAIN}" ]] && tag_exists "${NEXT_TAG}"; then
  echo "::error::next_version (${NEXT_PLAIN}) equals current_version and tag ${NEXT_TAG} already exists. Version detection likely failed — verify that commits follow Conventional Commits format and that fetch-depth: 0 is set."
  exit 1
fi

IFS='.' read -r MAJOR MINOR PATCH <<< "${NEXT_PLAIN}"
MAJOR_MINOR="${MAJOR}.${MINOR}"
MAJOR_MINOR_PATCH="${MAJOR}.${MINOR}.${PATCH}"

{
  echo "current_version=${CURRENT_PLAIN}"
  echo "next_version=${NEXT_PLAIN}"
  echo "major=${MAJOR}"
  echo "major_minor=${MAJOR_MINOR}"
  echo "major_minor_patch=${MAJOR_MINOR_PATCH}"
  echo "tag_major=${TAG_PREFIX}${MAJOR}"
  echo "tag_major_minor=${TAG_PREFIX}${MAJOR_MINOR}"
  echo "tag_major_minor_patch=${TAG_PREFIX}${MAJOR_MINOR_PATCH}"
} >> "${GITHUB_OUTPUT}"
