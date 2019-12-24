#!/usr/bin/env python3

import sys
import getopt
from re import search, match
import re

help = """
Поиск по SQL-Postgres дампу с удобным выводом

Синтакцис:
  ./sqldump_search.py <where> <what> [<num_lines> -B <num_lines> -A <num_lines> --notskip_bak_function]
    <where>        --название файла для поиска
    <what>         --текст, который надо найти
    <num_lines>    --выводить кол-во строк до и после найденного текста
    -B <num_lines> --выводить кол-во строк до найденного текста
    -A <num_lines> --выводить кол-во строк после найденного текста
    --notskip_bak_function     --искать в бэкапных функциях (которые оканчиваются на _bak[0-9]*)

Пример:
  ./sqldump_search.py text1 ./mydump.sql
  ./sqldump_search.py text1 ./mydump.sql 5
  ./sqldump_search.py text1 ./mydump.sql -B 1 -A 3

"""

out_before = 1
out_after = 1
notskip_bak_function = False

console_width = 80

color_red = "\033[1;31;40m"
color_green = "\033[1;32;40m"
color_yellow = "\033[1;33;40m"
color_blue = "\033[1;34;40m"
color_reset = "\033[0m"

try:
    options, remainder = getopt.gnu_getopt(
        sys.argv[1:],
        'B:A:h',
        ['before=',
         'after=',
         'notskip_bak_function',
         'help',
         ])
except getopt.GetoptError as err:
    print('ERROR: ', err)
    print(help)
    exit(1)

for opt, arg in options:
    if opt in ('-B', '--before'):
        out_before = int(arg)
    elif opt in ('-A', '--after'):
        out_after = int(arg)
    elif opt in ('--notskip_bak_function'):
        notskip_bak_function = True
    elif opt in ('-h', '--help'):
        print(help)
        exit(0)

if len(remainder) < 2 or 3 < len(remainder):
    print('ERROR: Неверный набор аргументов')
    print(help)
    exit(1)

file_name = remainder[0]
search_text = remainder[1]
if len(remainder) == 3:
    out_before = int(remainder[2])
    out_after = int(remainder[2])

#########################################################
def format_line_num(line_num):
    return color_yellow + str(line_num) + ": " + color_reset

def dot_delimiter():
    print(color_blue + "."*console_width + color_reset)

#########################################################
class ContextNone(object):
    def __init__(self):
        self.line = color_green + "Not in function context:" + color_reset + '\n'
        self.couted = False     # Контекст уже выведен в cout

    def cout(self, cur_line=None, search_text=None):
        if not self.couted:
            print(color_green + "#"*console_width + color_reset)
            sys.stdout.write(self.line)
            self.couted = True
            return True
        return False

    # Пропустить все из данного контекста
    def skip(self):
        return False


class Context(ContextNone):
    def __init__(self, quote_regex, line_num, line, name=None):
        super().__init__()
        self.quote_regex = quote_regex
        self.quote_opened = False
        self.line_num = line_num
        self.line = format_line_num(line_num) + line
        if name:
            self.line = self.line.replace(name, color_green + name + color_reset)
        self._skip = False

    def factory(line_num, line):
        if re.search("CREATE[ \t\n]+(OR[ \t\n]+REPLACE[ \t\n]+|)FUNCTION[ \t\n]+(.*)[ \t\n]+", line, re.IGNORECASE):
            return ContextFunction(line_num, line)
        if re.search("COMMENT[ \t\n]+ON[ \t\n]+[A-z \t\n]+[ \t\n]+IS[ \t\n]+", line, re.IGNORECASE):
            return ContextComment(line_num, line)
    factory = staticmethod(factory)

    def _quote_matched(self, line):
        return (re.search(self.quote_regex, line) is not None)

    def process(self, line):
        if self._quote_matched(line):
            if self.quote_opened:
                return ContextNone()
            self.quote_opened = True
        return self

    def cout(self, cur_line, search_text):
        if self.line_num == cur_line:
            self.line = self.line.replace(search_text, color_red + search_text + color_reset)
        return super().cout()

    # Пропустить все из данного контекста
    def skip(self):
        return self._skip


class ContextFunction(Context):
    def __init__(self, line_num, line):
        self._name = search("FUNCTION[ ]*([A-z0-9.]*)[ (]*", line, re.IGNORECASE).group(1)
        super().__init__("\$([A-z]*)\$", line_num, line, self._name)
        self.quote_opened = self._quote_matched(line)    # проверяем наличие открывающего маркера в той же строке с найденным именем контекста

        if not notskip_bak_function:
            self._skip = (match(".*?(_(bak|trash)[0-9]*)", self._name) is not None)

    # Переопределим "маркер тела функции" в соотвествии с первым найденным
    def _quote_matched(self, line):
        res = re.search(self.quote_regex, line)
        if (res is not None):
            if not self.quote_opened:
                self.quote_regex = "\$" + res.group(1) + "\$"
            return True
        return False

class ContextComment(Context):
    def __init__(self, line_num, line):
        self._name = search("COMMENT[ \t\n]+ON[ \t\n]+([A-z \t\n]+[ \t\n]+)IS[ \t\n]+", line, re.IGNORECASE).group(1)
        super().__init__("([^']|^)'([^']|$)", line_num, line, self._name)
        self.quote_opened = self._quote_matched(line)    # проверяем наличие открывающего маркера в той же строке с найденным именем контекста


#########################################################
# f            --"actual" file object
# f_follower   --file object which'll be used for printing "before" lines. It'll be lag from f
with open(file_name, 'r') as f, open(file_name, 'r') as f_follower:
    context = ContextNone()
    print_next_lines_count = 0  # кол-во строк, которое необходимо еще напечатать
    last_printed_line_num = 0   # номер последней выведенной строки
    line_num = 0
    line_num_follower = 0
    for line in f:
        line_num = line_num + 1

        if type(context).__name__ == "ContextNone":
            new_context = Context.factory(line_num, line)
            if new_context is not None:
                context = new_context
                print_next_lines_count = 0  # если встречается новая функция, то не печатаем строки после последней найденной
        else:
            context = context.process(line)
            if context.skip():
                continue

        # ищем целевую строку поиска
        if search(search_text, line, re.IGNORECASE):
            # Пропускаем если это комментарий
            if re.search("^[ \t\n]*--", line) is not None:
                continue

            # Выводим название контекста
            if context.cout(line_num, search_text) and type(context).__name__ != "ContextNone":
                last_printed_line_num = context.line_num

            #########################################
            # Вывести строки перед найденной строкой
            line_num_start = max(line_num - out_before, last_printed_line_num + 1)
            # Будем выводить строки из непечатаемой зоны, когда разрыв между прошлой печатной строкой и следующей < 3 строк
            if (line_num_start - last_printed_line_num) < 4:
                line_num_start = last_printed_line_num + 1

            if (line_num_start - 1) > last_printed_line_num:
                dot_delimiter()

            if out_before > 0:
                # пропустить ненужные строки
                while (line_num_follower < (line_num_start -1)):
                    line_num_follower = line_num_follower + 1
                    f_follower.readline()
                # вывести заданное кол-во строк перед найденной строкой
                while (line_num_follower < (line_num - 1)):
                    line_num_follower = line_num_follower + 1
                    sys.stdout.write(format_line_num(line_num_follower) + f_follower.readline())
            #########################################

            if line_num != last_printed_line_num:
                # Выводим найденную строку
                sys.stdout.write(format_line_num(line_num) + line.replace(search_text, color_red + search_text + color_reset))
            print_next_lines_count = out_after
            last_printed_line_num = line_num

        elif print_next_lines_count != 0:
            # Выводим строки после найденной строки
            sys.stdout.write(format_line_num(line_num) + line)
            print_next_lines_count = print_next_lines_count - 1
            last_printed_line_num = line_num
