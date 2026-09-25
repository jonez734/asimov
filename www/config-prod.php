<?php

require_once('/srv/www/bbsengine6/php/bootstrap.php');
require_once('util.php');
\bbsengine6\util\add_include_paths(['/srv/www/zoid6/php/', '/srv/www/bbsengine6/php/', '/srv/www/smarty/']);

// Define configuration constants in config namespace (required by bbsengine6)
// Using backslash prefix makes them accessible via defined('\config\CONSTANT')
define("config\SITEADMINEMAIL", "asimov <asimov@projects.zoidtechnologies.com>");
define("config\SITENAME", "asimov");
define("config\SITETITLE", "Project Asimov - Robotics, AI, and Augmented Reality");
define("config\SITEURL", "/asimov/");
define("config\SITEDESCRIPTION", "Asimov");
define("config\VHOSTDIR", "/srv/www/vhosts/zoidtechnologies.com/");
define("config\DOCUMENTROOT", \config\VHOSTDIR . "html/asimov/");
define("config\SKINDIR", \config\DOCUMENTROOT . "skin/");
define("config\SKINURL", \config\SITEURL . "skin/");
define("config\JSURL", "/asimov/skin/js/");
define("config\IMAGESURL", "https://zoidtechnologies.com/static/");

// Define URL constants BEFORE zoid6config.php so they're available for templates
define("config\SHAREDSKINURL", "/shared/skin/");
define("config\ENGINESKINURL", "/engine/skin/");
define("config\ENGINEURL", "/engine/");

// @since 2026-09-24 — load zoid6config.php first (transitively
// loads bbsengine6config.php, defining config\SHAREDTMPLDIR)
// before the SMARTY* defines that reference it.
require_once('zoid6config.php');

// SMARTYTEMPLATESDIR - 3-element array (bbsengine6/skin/tmpl/ is
// auto-appended by bbsengine6config.php as the engine fallback).
// Search order: 1) Site-specific templates 2) legacy structure 3) shared zoid6 templates
define("config\SMARTYTEMPLATESDIR", [
    0 => \config\SKINDIR . "tmpl/",
    1 => \config\DOCUMENTROOT . "tmpl/",
    2 => \config\SHAREDTMPLDIR,
]);

// SMARTYCOMPILEDTEMPLATESDIR - compiled template cache directory
define("config\SMARTYCOMPILEDTEMPLATESDIR", \config\VHOSTDIR . "templates_c");

// SMARTYPLUGINSDIR - plugin directories for custom Smarty functions and modifiers
define("config\SMARTYPLUGINSDIR", [
    0 => \config\VHOSTDIR . "smarty/",
    1 => "/srv/www/zoid6/smarty/"
]);

define("config\LOGENTRYPREFIX", "asimovprod");
define("config\GOOGLEANALYTICSACCOUNT", "UA-23705021-1");
define("config\SECTIONTEMPLATEDIR", \config\SKINDIR . "tmpl/sections/");

// Create global aliases for non-SMARTY constants
// (SMARTY* aliases are created by zoid6config.php)
define("SITEURL", \config\SITEURL);
define("VHOSTDIR", \config\VHOSTDIR);
define("DOCUMENTROOT", \config\DOCUMENTROOT);
define("SKINDIR", \config\SKINDIR);
define("SKINURL", \config\SKINURL);
define("JSURL", \config\JSURL);
define("ENGINEURL", \config\ENGINEURL);
define("IMAGESURL", \config\IMAGESURL);
define("LOGENTRYPREFIX", \config\LOGENTRYPREFIX);
define("SECTIONTEMPLATEDIR", \config\SECTIONTEMPLATEDIR);
define("SHAREDSKINURL", \config\SHAREDSKINURL);
define("ENGINESKINURL", \config\ENGINESKINURL);

?>
