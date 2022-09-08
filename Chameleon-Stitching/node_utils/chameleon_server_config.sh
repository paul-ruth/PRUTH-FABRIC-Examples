# Install Packages
#sudo apt-get update -y -q
#sudo apt-get install -y -q python3-manilaclient net-tools iperf3 default-jre iftop apache2
sudo yum install -y -q net-tools iperf3 iftop httpd java-latest-openjdk vim

# Setup keys for ssh between hosts. Here we use a keypair that is also available on Chameleon
#cp private_config/my_chameleon_key* ~/.ssh/.
#chmod 600 ~/.ssh/my_chameleon_key*
#cat ~/.ssh/my_chameleon_key.pub >> ~/.ssh/authorized_keys 

# Start ssh-agent
#eval "$(ssh-agent -s)"
#ssh-add ~/.ssh/my_chameleon_key

# Mount the share
sudo mount -t nfs -o nfsvers=4.2,proto=tcp 10.31.0.14:/volumes/_nogroup/02f14a95-75e9-48f4-93cb-6b718e5f8efa/c72a7545-b1b2-48b2-9a4e-828c3a9ae26d /var/www/html

# Turn on apache
#sudo systemctl start apache2
sudo systemctl start httpd

# Add this to /etc/apache2/ports.conf (Replaces 'Listen 80'
#Listen 10.129.129.89:80 