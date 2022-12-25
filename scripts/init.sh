while true
do
    echo 'pulling new changes'
    git config --global --add safe.directory /home/pi/git/ProjectIvy.Proximity
    git pull

    echo 'running python script'
    sudo -E python3 scripts/main.py
done