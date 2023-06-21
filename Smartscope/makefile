# dev mode
dev-install:
	virtualenv venv
	. venv/bin/activate && (\
		export mode=dev \
		pip3 install -r requirements.txt \
	)

dev-run:
	. venv/bin/activate && (\
		python3 bin/manage.py runserver --settings=core.settings.settings_dev \
	)

clean:
	@rm -fr venv
	@find -iname "*.pyc" -delete