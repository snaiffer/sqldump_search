#!/usr/bin/env python3

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
  ./sqldump_search.py text1 ./mydump.sql -B 1 -A 3

"""

import sys
import getopt
from re import search, match
import re

out_before = 1
out_after = 1
notskip_bak_function = False

console_width = 80

color_red="\033[1;31;40m"
color_green="\033[1;32;40m"
color_yellow="\033[1;33;40m"
color_blue="\033[1;34;40m"
color_reset="\033[0m"

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

def out_line_num(line_num):
    return color_yellow + str(line_num) + ": " + color_reset

# f            --"actual" file object
# f_follower   --file object which'll be used for printing "before" lines. It'll be lag from f
with open(file_name, 'r') as f, open(file_name, 'r') as f_follower:
    cur_function_line = ""
    cur_function_line_num = 0
    cur_context_printed = False
    dollar_quotes_opened = False    # сейчас читается тело функции. Доллар кавычки открыты или нет.
    print_next_lines_count = 0  # кол-во строк, которое необходимо еще напечатать
    last_printed_line_num = 0   # номер последней выведенной строки
    line_num = 0
    line_num_follower = 0
    skip_cur_function = False   # пропустить бэкапные функции
    for line in f:
        line_num = line_num + 1

        if not cur_function_line:
            # ищем название функции
            cur_function_line_match = match("CREATE.*FUNCTION.*(.*).*", line, re.IGNORECASE)
            if cur_function_line_match != None:
                cur_function_line = out_line_num(line_num) + line
                cur_function_line_num = line_num
                print_next_lines_count = 0  # если встречается новая функция, то не печатаем строки после последней найденной
                continue
        else:
            if search("\$[A-z]*\$", line) != None:
                if dollar_quotes_opened:    # Тело функции закончилось
                    cur_function_line = ""
                    cur_context_printed = False
                    skip_cur_function = False
                dollar_quotes_opened = not dollar_quotes_opened
            elif skip_cur_function:
                continue

        # ищем целевую строку поиска
        if search(search_text, line, re.IGNORECASE):
            # Выводим контекст для найденной строки:
            if not cur_context_printed:
                print(color_green + "#"*console_width + color_reset)
                #   * название функции
                if cur_function_line:
                    cur_function_name = search("FUNCTION[ ]*([A-z0-9.]*)[ (]*", cur_function_line).group(1)
                    if not notskip_bak_function:   # пропустить бэкапные функции
                        if match(".*?(_bak[0-9]*)", cur_function_name) != None:
                            skip_cur_function = True
                            continue
                    sys.stdout.write(cur_function_line.replace(cur_function_name, color_green + cur_function_name + color_reset))
                    last_printed_line_num = cur_function_line_num
                #   * нет контекста
                else:
                    print(color_green + "Not in function context:" + color_reset)

                cur_context_printed = True
            #########################################

            line_num_start = max(line_num - out_before, last_printed_line_num)

            if line_num_start > last_printed_line_num:
                print(color_blue + "."*console_width + color_reset)

            # Вывести строки перед найденной строкой
            if out_before > 0:
                while ( line_num_follower < (line_num_start - 1) ):
                    line_num_follower = line_num_follower + 1
                    f_follower.readline()

                while (line_num_follower < (line_num - 1) ):
                    line_num_follower = line_num_follower + 1
                    sys.stdout.write(out_line_num(line_num_follower) + f_follower.readline())
            #########################################

            # Выводим найденную строку
            sys.stdout.write(out_line_num(line_num) + line.replace(search_text, color_red + search_text + color_reset))
            print_next_lines_count = out_after
            last_printed_line_num = line_num

        elif print_next_lines_count != 0:
            sys.stdout.write(out_line_num(line_num) + line)
            print_next_lines_count = print_next_lines_count - 1
            last_printed_line_num = line_num

#if __name__ == "__main__":
