#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPUTE_SCRIPT="${SCRIPT_DIR}/../compute.sh"
TEST_ROOT="${TMPDIR:-/tmp}/version-get-tests-$$"
CLIFF_BIN="$(command -v git-cliff)"

cleanup() {
  rm -rf "${TEST_ROOT}"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_output() {
  local output="$1"
  local key="$2"
  local expected="$3"
  local actual

  actual="$(grep -E "^${key}=" "${output}" | tail -1 | cut -d= -f2-)"
  [[ "${actual}" == "${expected}" ]] ||
    fail "expected ${key}=${expected}, got ${actual:-<missing>}"
}

init_repo() {
  local repo="$1"

  mkdir -p "${repo}"
  git -C "${repo}" init -q
  git -C "${repo}" config user.name "Version Tests"
  git -C "${repo}" config user.email "version-tests@example.com"
}

commit_file() {
  local repo="$1"
  local message="$2"
  local content="$3"

  printf '%s\n' "${content}" >> "${repo}/history.txt"
  git -C "${repo}" add history.txt
  git -C "${repo}" commit -qm "${message}"
}

compute() {
  local repo="$1"
  local output="$2"
  local prefix="$3"
  local default="$4"
  local force="${5:-}"
  local fail_on_default="${6:-false}"
  local fail_on_same="${7:-true}"
  local cliff_bin="${8:-${CLIFF_BIN}}"
  local svu_bin="${9:-svu}"

  : > "${output}"
  (
    cd "${repo}"
    GITHUB_OUTPUT="${output}" \
      DEFAULT_VERSION="${default}" \
      TAG_PREFIX="${prefix}" \
      FORCE_NEXT_VERSION="${force}" \
      FAIL_ON_DEFAULT="${fail_on_default}" \
      FAIL_ON_SAME_VERSION="${fail_on_same}" \
      GIT_CLIFF_BIN="${cliff_bin}" \
      SVU_BIN="${svu_bin}" \
      bash "${COMPUTE_SCRIPT}"
  )
}

expect_failure() {
  local description="$1"
  shift

  if "$@" >/dev/null 2>&1; then
    fail "${description} unexpectedly succeeded"
  fi
}

mkdir -p "${TEST_ROOT}"

mixed="${TEST_ROOT}/mixed"
init_repo "${mixed}"
cat > "${mixed}/cliff.toml" <<'EOF'
[git]
tag_pattern = "v[0-9]+\\.[0-9]+\\.[0-9]+$"
EOF
commit_file "${mixed}" "chore: initial client" "client"
git -C "${mixed}" tag v1.2.3
git -C "${mixed}" tag v1
git -C "${mixed}" tag v1.2

commit_file "${mixed}" "feat(gateway): add route" "gateway"
git -C "${mixed}" tag gateway-v4.5.6
git -C "${mixed}" tag gateway-v4
git -C "${mixed}" tag gateway-v4.5

commit_file "${mixed}" "fix(website): repair page" "website"
git -C "${mixed}" tag website-v2.0.1
commit_file "${mixed}" "docs: update guide" "documentation"
git -C "${mixed}" tag v1x2x9
git -C "${mixed}" tag gateway-v4x5x9
git -C "${mixed}" tag website-v2x0x9

client_output="${TEST_ROOT}/client.out"
compute "${mixed}" "${client_output}" v v0.1.0
assert_output "${client_output}" current_version 1.2.3
assert_output "${client_output}" next_version 1.3.0
assert_output "${client_output}" major 1
assert_output "${client_output}" major_minor 1.3
assert_output "${client_output}" major_minor_patch 1.3.0
assert_output "${client_output}" tag_major v1
assert_output "${client_output}" tag_major_minor v1.3
assert_output "${client_output}" tag_major_minor_patch v1.3.0

gateway_output="${TEST_ROOT}/gateway.out"
compute "${mixed}" "${gateway_output}" gateway-v gateway-v0.1.0
assert_output "${gateway_output}" current_version 4.5.6
assert_output "${gateway_output}" next_version 4.5.7
assert_output "${gateway_output}" tag_major gateway-v4
assert_output "${gateway_output}" tag_major_minor gateway-v4.5
assert_output "${gateway_output}" tag_major_minor_patch gateway-v4.5.7

website_output="${TEST_ROOT}/website.out"
compute "${mixed}" "${website_output}" website-v website-v0.1.0
assert_output "${website_output}" current_version 2.0.1
assert_output "${website_output}" next_version 2.0.2
assert_output "${website_output}" tag_major_minor_patch website-v2.0.2

missing_output="${TEST_ROOT}/missing.out"
compute "${mixed}" "${missing_output}" api-v 0.4.0
assert_output "${missing_output}" current_version 0.4.0
assert_output "${missing_output}" next_version 0.4.0
assert_output "${missing_output}" tag_major_minor_patch api-v0.4.0

forced_plain_output="${TEST_ROOT}/forced-plain.out"
compute "${mixed}" "${forced_plain_output}" gateway-v gateway-v0.1.0 9.8.7
assert_output "${forced_plain_output}" next_version 9.8.7
assert_output "${forced_plain_output}" tag_major_minor_patch gateway-v9.8.7

forced_tag_output="${TEST_ROOT}/forced-tag.out"
compute "${mixed}" "${forced_tag_output}" gateway-v gateway-v0.1.0 gateway-v9.8.8
assert_output "${forced_tag_output}" next_version 9.8.8
assert_output "${forced_tag_output}" tag_major_minor_patch gateway-v9.8.8

expect_failure \
  "forcing another stream's full tag" \
  compute "${mixed}" "${TEST_ROOT}/wrong-force.out" gateway-v gateway-v0.1.0 website-v9.8.9

expect_failure \
  "forcing a duplicate tag" \
  compute "${mixed}" "${TEST_ROOT}/duplicate-force.out" gateway-v gateway-v0.1.0 gateway-v4.5.6

fake_cliff="${TEST_ROOT}/fake-cliff"
cat > "${fake_cliff}" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "${FAKE_CLIFF_VERSION}"
EOF
chmod +x "${fake_cliff}"

same_repo="${TEST_ROOT}/same"
init_repo "${same_repo}"
commit_file "${same_repo}" "chore: release" "release"
git -C "${same_repo}" tag gateway-v2.0.0

same_output="${TEST_ROOT}/same.out"
export FAKE_CLIFF_VERSION=gateway-v2.0.0
expect_failure \
  "the same-version guard for a prefixed tag" \
  compute "${same_repo}" "${same_output}" gateway-v gateway-v0.1.0 "" false true "${fake_cliff}"
compute "${same_repo}" "${same_output}" gateway-v gateway-v0.1.0 "" false false "${fake_cliff}"
assert_output "${same_output}" tag_major_minor_patch gateway-v2.0.0

export FAKE_CLIFF_VERSION=gateway-v0.1.0
expect_failure \
  "falling back to the prefixed default when stream history exists" \
  compute "${same_repo}" "${TEST_ROOT}/default.out" gateway-v gateway-v0.1.0 "" true false "${fake_cliff}"

empty_cliff="${TEST_ROOT}/empty-cliff"
cat > "${empty_cliff}" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "${empty_cliff}"

fallback_output="${TEST_ROOT}/fallback.out"
compute "${same_repo}" "${fallback_output}" gateway-v gateway-v0.1.0 "" false true "${empty_cliff}"
assert_output "${fallback_output}" current_version 2.0.0
assert_output "${fallback_output}" next_version 2.0.1
assert_output "${fallback_output}" tag_major_minor_patch gateway-v2.0.1

empty_svu="${TEST_ROOT}/empty-svu"
cp "${empty_cliff}" "${empty_svu}"
expect_failure \
  "an unusable svu fallback" \
  compute "${same_repo}" "${TEST_ROOT}/fallback-failure.out" gateway-v gateway-v0.1.0 "" false true "${empty_cliff}" "${empty_svu}"

echo "All version/get release-stream tests passed."
