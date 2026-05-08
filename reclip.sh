#!/bin/bash
cd /home/mscalora/dev/reclip
source venv/bin/activate
export FLASK_SECRET_KEY="replace_this_with_a_secure_random_key_in_production"
flask run --host=127.0.0.1 --port=8899
