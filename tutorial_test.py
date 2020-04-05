
# TODO: abstraction
# TODO: progress report



def test_final():

    # ANCHOR: common_imports
    import os
    from keyword     import iskeyword
    from collections import Counter
    # ANCHOR_END: common_imports

    # ANCHOR: liquidata_imports
    from liquidata import pipe, name as NAME, get as GET, put as PUT, join as JOIN, out as OUT, into as INTO, use
    # ANCHOR_END: liquidata_imports

    # ANCHOR: liquidata_full
    keyword_frequency_pipe = pipe(
        os.walk, JOIN,
        NAME.path.dirs.files,
        GET.files * (JOIN, { use(str.endswith, '.py') }) >> PUT.filename,
        GET.path.filename * os.path.join,
        open, JOIN,
        use(str.split, '#', maxsplit=1),
        GET[0],
        str.split, JOIN,
        { iskeyword },
        OUT(INTO(Counter)))
    # ANCHOR_END: liquidata_full

    # ANCHOR: liquidata_abstracted_full
    all_files         = os.walk, JOIN, NAME.path.dirs.files
    pick_python_files = GET.files * (JOIN, { use(str.endswith, '.py') }) >> PUT.filename
    file_contents     = GET.path.filename * os.path.join, open, JOIN
    ignore_comments   = use(str.split, '#', maxsplit=1), GET[0]
    find_keywords     = str.split, JOIN, { iskeyword }

    keyword_frequency_pipe = pipe(
        all_files,
        pick_python_files,
        file_contents,
        ignore_comments,
        find_keywords,
        OUT(INTO(Counter)))
    # ANCHOR_END: liquidata_abstracted_full

    # ANCHOR: pure_python_full
    def keyword_frequency_loop(directories):
        counter = Counter()
        for directory in directories:
            for (path, dirs, files) in os.walk(directory):
                for filename in files:
                    if not filename.endswith('.py'):
                        continue
                    for line in open(os.path.join(path, filename)):
                        for name in line.split('#', maxsplit=1)[0].split():
                            if iskeyword(name):
                                counter[name] += 1
        return counter
    # ANCHOR_END: pure_python_full

    directories = ['/home/jacek/src']
    PIPE = keyword_frequency_pipe(directories)
    LOOP = keyword_frequency_loop(directories)

    assert PIPE == LOOP
