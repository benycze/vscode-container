# Source the enviroment 
if [ -f /etc/bashrc ]; then
        . /etc/bashrc
fi

# Start SSH if it's not already running
if [ `ps aux | grep -c ssh[d]` -eq 0 ] ; then
  run-ssh
fi

# Run the Apache 2
if [ -f /etc/lsb-release ]; then
   echo "Starting apache2 on ubuntu"
   if [ `ps aux | grep -c apache2` -eq 0 ] ; then
     service apache2 start
   fi
else
   echo "Starting apache2 on almalinux"
   if [ `ps aux | grep -c http[d]` -eq 0 ] ; then
     httpd
   fi
fi

echo "************************************************************"
echo "* VScode Docker image is running ..."
echo "************************************************************"
