load_test(){
  echo "Run test $1"
  aws sts get-caller-identity --profile IamCredentialsApi
}
# For loop 5 times
for i in {1..5}
do
	load_test $i & # Put a function in the background
done
