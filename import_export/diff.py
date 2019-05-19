def diff_lines_to_words(text1, text2):
    # Implemented following the docs:
    # https://github.com/google/diff-match-patch/wiki/Line-or-Word-Diffs
    # Only one line is different from diff_linesToChars.
    # line_end = text.find('\n', lineStart)
    # --->
    # line_end = text.find(' ', lineStart)
    # Variable names are also changed to snake_case for code integrity.

    line_array = []
    line_hash = {}
    line_array.append('')

    def diff_lines_to_chars_munge(text):
        chars = []
        line_start = 0
        line_end = -1
        while line_end < len(text) - 1:
            line_end = text.find(' ', line_start)
            if line_end == -1:
                line_end = len(text) - 1
            line = text[line_start:line_end + 1]

            if line in line_hash:
                chars.append(chr(line_hash[line]))
            else:
                if len(line_array) == max_lines:
                    line = text[line_start:]
                    line_end = len(text)
                line_array.append(line)
                line_hash[line] = len(line_array) - 1
                chars.append(chr(len(line_array) - 1))
            line_start = line_end + 1
        return "".join(chars)

    max_lines = 666666
    chars1 = diff_lines_to_chars_munge(text1)
    max_lines = 1114111
    chars2 = diff_lines_to_chars_munge(text2)
    return (chars1, chars2, line_array)
