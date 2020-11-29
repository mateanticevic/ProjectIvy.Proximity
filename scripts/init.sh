while true
do
    echo 'pulling new changes'
    git pull

    echo 'running python script'
    sudo -E python3 scripts/main.py
done