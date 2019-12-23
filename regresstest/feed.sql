
Create function test1(a int)
    LANGUAGE plpgsql SECURITY DEFINER ROWS 5
    AS $$
-- select * from ext.plpgsql_check_function('test1(int)')
declare
	_r record;
	_count int;

begin
target_11
line 1
target_12
line 2
line 3
line 4
target_13
line 5
line 6
line 7
target_14
end
$$;


comment on schema person is '
target_21
line 1
target_22
line 2
line 3
line 4
target_23
line 5
target_111
line 6
line 7
line 8
target_24
'


Create function test2(a int)
LANGUAGE plpgsql
AS $function$
begin
  $$
  target_31
end
$function$


line_51
target_41
line_53

-- target_51
  -- target_51
not_comment -- target_51
