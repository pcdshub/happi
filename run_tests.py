#!/usr/bin/env python
import logging
import sys

import pytest

if __name__ == '__main__':
    # Show output results from every test function
    # Show the message output for skipped and expected failures
    args = ['-v', '-vrxs']

    # Add extra arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    print('pytest arguments: {}'.format(args))

    logging.basicConfig(level=logging.DEBUG)
    sys.exit(pytest.main(args))
