#!/bin/bash

ISSUE=$1
shift
DESCRIPTION=$*

if [[ -z "$ISSUE" || -z "$DESCRIPTION" ]]; then
    echo "Usage: $0 (ISSUE NUMBER) (DESCRIPTION)"
    exit 1
fi

echo "Issue: $ISSUE"
echo "Description: $DESCRIPTION"

FILENAME=source/upcoming_release_notes/${ISSUE}-${DESCRIPTION// /_}.rst

pushd "$(dirname "$0")" || exit 1

sed -e "s/IssueNumber Title/${ISSUE} ${DESCRIPTION}/" \
    "source/upcoming_release_notes/template-short.rst" > "${FILENAME}"

if ${EDITOR} "${FILENAME}"; then
    echo "Adding ${FILENAME} to the git repository..."
    git add "${FILENAME}"
fi

popd
