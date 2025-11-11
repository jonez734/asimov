<?php

namespace {
    /*
     * @since 20190817
     * @since 20221104
     */
    $includepath = get_include_path().":/srv/www/zoid6/php:/srv/www/bbsengine6/php/:/srv/www/smarty/";
    if (set_include_path($includepath) === false)
    {
        print("include path fail");
    }

    // require_once("zoid6.php");
}

namespace config {

    define("SITEADMINEMAIL", "achilles <achilles@projects.zoidtechnologies.com>");

    define("SITETITLE", "Project Achilles - A study of the affects of flavor enhancers on health");
    define("SITEURL", "https://zoidtechnologies.com/achilles/");
    define("SITEKEYWORDS", "project achilles, monosodium glutamate, mono-sodium glutamate, msg, glutamate, disodium glutamate, truth in labeling, health, nutrition, consumer protection, food additives");
    define("SITEDESCRIPTION", "Project Achilles studies the affects of flavor enhancers on health");
    //define("SITETYPE", "website");

    //define("SYSTEMDSN", "pgsql://apache@127.0.0.1/zoidweb3"); @see zoid6
    //define("SYSTEMDSN", \zoid6\SYSTEMDSN);
    //define("config\SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6"); @see zoid6.php

    define("config\VHOSTDIR", "/srv/www/vhosts/zoidtechnologies.com/html/achilles/");
    define("DOCUMENTROOT", \config\VHOSTDIR);

    define("SKINDIR", DOCUMENTROOT . "skin/");
    define("SKINURL", SITEURL . "skin/");
    
    define("JSURL", "/achilles/js/");

    define("IMAGESURL", "https://zoidtechnologies.com/static/");

/*
    define("SMARTYCOMPILEDTEMPLATESDIR", VHOSTDIR . "templates_c");
    define("SMARTYPLUGINSDIR", [ 0 => VHOSTDIR . "smarty/", 1 => "/srv/www/zoid6/smarty/"]);
    define("SMARTYTEMPLATESDIR", [ 0 => VHOSTDIR . "tmpl/", 1=> "/srv/www/zoid6/skin/tmpl/", 2 => "/srv/www/bbsengine6/skin/tmpl/"]);
*/

    define("config\LOGENTRYPREFIX", "achillesprod");

//    define("STATICSKINURL", "/static/skin/");

    // define("ENGINEURL", "https://engine.zoidtechnologies.com/"); @see zoid6

    /**
     * @since 20200422
     * 3
     */
    define("GOOGLEANALYTICSACCOUNT", "UA-23705021-1");
} /* config namespace */
?>
