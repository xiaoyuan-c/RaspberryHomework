python -c "print('hello')"
python3 -c "import os; os.system('id')"
python3 - <<'PY'
print("hello")
PY

python <<EOF
import os
print(os.getcwd())
EOF

bash -c "echo hello"
sh -c 'id'
node -e "console.log(1)"
perl -e 'print "hello";'
ruby -e 'puts 123'

cat <<'PY' | python3
print("hello")
PY
