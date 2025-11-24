embedder.py + extracter.py + main.py - > updateds the entire vector db with whatever data is there in Postgres
##RUN
python main.py

course_updater.py - > updates a specific course in the vector db from Postgres
##RUN
(COURSE_ID = Add your course_id here)
python course_updater.py