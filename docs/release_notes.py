import sys
import time
from collections import defaultdict
from pathlib import Path

# find the pre-release directory and release notes file
THIS_DIR = Path(__file__).resolve().parent
PRE_RELEASE = THIS_DIR / 'source' / 'upcoming_release_notes'
TEMPLATE = PRE_RELEASE / 'template-short.rst'
RELEASE_NOTES = THIS_DIR / 'source' / 'releases.rst'

# Set up underline constants
TITLE_UNDER = '#'
RELEASE_UNDER = '='
SECTION_UNDER = '-'


def parse_pre_release_file(path):
    """
    Return dict mapping of release notes section to lines.

    Uses empty list when no info was entered for the section.
    """
    print(f'Checking {path} for release notes.')
    with path.open('r') as fd:
        lines = fd.readlines()

    section_dict = defaultdict(list)
    prev = None
    section = None

    for line in lines:
        if prev is not None:
            if line.startswith(SECTION_UNDER * 2):
                section = prev.strip()
                continue
            if section is not None and line[0] in ' -':
                notes = section_dict[section]
                if len(line) > 6:
                    notes.append(line)
                section_dict[section] = notes
        prev = line

    return section_dict


def extend_release_notes(path, version, release_notes):
    """
    Given dict mapping of section to lines, extend the release notes file.
    """
    with path.open('r') as fd:
        lines = fd.readlines()

    new_lines = ['\n', '\n']
    date = time.strftime('%Y-%m-%d')
    release_title = f'{version} ({date})'
    new_lines.append(release_title + '\n')
    new_lines.append(len(release_title) * RELEASE_UNDER + '\n')
    new_lines.append('\n')
    for section, section_lines in release_notes.items():
        if section == 'Contributors':
            section_lines = sorted(list(set(section_lines)))
        if len(section_lines) > 0:
            new_lines.append(section + '\n')
            new_lines.append(SECTION_UNDER * len(section) + '\n')
            new_lines.extend(section_lines)
            new_lines.append('\n')

    output_lines = lines[:2] + new_lines + lines[2:]

    print('Writing out release notes file')
    for line in new_lines:
        print(line.strip('\n'))
    with path.open('w') as fd:
        fd.writelines(output_lines)


def main(version):
    section_notes = parse_pre_release_file(TEMPLATE)
    for path in PRE_RELEASE.iterdir():
        if path.name[0] in '1234567890':
            extra_notes = parse_pre_release_file(path)
            for section, notes in section_notes.items():
                notes.extend(extra_notes[section])
                section_notes[section] = notes

    extend_release_notes(RELEASE_NOTES, version, section_notes)

    # git rm all of the pre-release files
    # git add the new release notes file


if __name__ == '__main__':
    main(sys.argv[1])
