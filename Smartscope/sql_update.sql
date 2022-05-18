-- v0.6
RENAME TABLE 
`autoscreenViewer_atlasmodel` TO `altasmodel`,
`autoscreenViewer_autoloadergrid` TO `autoloadergrid`,
`autoscreenViewer_detector` TO `detector`,
`autoscreenViewer_finder` TO `finder`,
`autoscreenViewer_changelog` TO `changelog`,
`autoscreenViewer_gridcollectionparams` to `gridcollectionparams`,
`autoscreenViewer_highmagmodel` TO `highmagmodel`,
`autoscreenViewer_holemodel` TO `holemodel`,
`autoscreenViewer_holetype` TO `holetype`,
`autoscreenViewer_meshmaterial` TO `meshmaterial`,
`autoscreenViewer_meshsize` to `meshsize`,
`autoscreenViewer_microscope` TO `microscope`,
`autoscreenViewer_process` to `process`,
`autoscreenViewer_screeningsession` to `screeningsession`,
`autoscreenViewer_squaremodel` to `squaremodel`;

UPDATE django_content_type SET app_label = 'API' WHERE app_label = 'autoscreenViewer';
UPDATE django_migrations SET app = 'API' WHERE app = 'autoscreenViewer';

UPDATE changelog SET table_name=REPLACE(table_name,'autoscreenViewer_','') WHERE table_name LIKE 'autoscreenViewer%';
ALTER TABLE detector ADD COLUMN `alignframes_rotflip` integer NULL;

-- dev
