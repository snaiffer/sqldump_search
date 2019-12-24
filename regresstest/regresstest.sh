#!/bin/bash

check() {
  CMD=$1
  DESC=$2
  echo >> result
  echo $DESC >> result
  echo "COMMAND: $CMD" >> result
  eval $CMD >> result
  return 0
}

#################################
rm -f ./result

check "../sqldump_search.py feed.sql 'a int'" '# Фрагмент поиска попадает в строку с контекстом'

check "../sqldump_search.py feed.sql 'ROWS 5'" '# Строка с фрагментом поиска является предыдущей для строки с контесктом'

check "../sqldump_search.py feed.sql 'target_1'" '# Фрагмент поиска встречается несколько раз в разных контекстах'

check "../sqldump_search.py feed.sql 'target_31'" '# Проверка корректного определения области контекста функции, когда маркер = $<name>$, а в контексте встречается $$
# Проверка вывода строк из непечатаемой зоны, когда разрыв между прошлой печатной строкой и следующей < 3 строк'

check "../sqldump_search.py feed.sql 'target_2'" '# Проверка вывода символов разрыва вывода (".............")
# v2 Проверка вывода строк из непечатаемой зоны, когда разрыв между прошлой печатной строкой и следующей < 3 строк'

check "../sqldump_search.py feed.sql 'target_41'" '# Проверка поиска не в контексте'

check "../sqldump_search.py feed.sql 'target_13' 3" '# Тестирование вывода строк до и после = переданному параметру'

check "../sqldump_search.py feed.sql 'target_51'" '# Пропускаем, если строка поиска содержится в комментарии SQL'

check "../sqldump_search.py feed.sql 'target_61'" '# Пропускаем поиск в контексте, если имя контекста соотвествует бэкапной функции (_bak, _trash)'

#################################
diff ./result ./result.good
if [ $? = 0 ]; then
  echo "Success"
fi;

