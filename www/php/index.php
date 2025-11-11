<?php

require_once("config.php");

require_once("engine.php");
require_once("session.php");
require_once("database.php");

require_once("zoid6.php");
require_once("libvulcan.php");

class index
{
  function gethealthlinks()
  {
    return [];

    $sql = "select elle.url from vulcan.link as elle, vulcan.map_link_sig as m where m.url = elle.url and m.path ~ 'top.achilles' order by elle.broken asc, lastmodified desc";

    $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
    $dat = [];

    $stmt = $pdo->prepare($sql);
//    try {
      $stmt->execute($dat);
//    } catch (Exception $e) {
//      return null;
//    }
    if ($stmt->rowCount() == 0)
    {
      return [];
    }
    $res = $stmt->fetchAll();
    $healthlinks = [];
    foreach ($res as $rec)
    {
      $link = \vulcan\lib\getlinkbyurl($rec["url"]);
      $healthlinks[] = $link;
      if (\vulcan\lib\access("view", $link) === true)
      {
        $healthlinks[] = $link;
      }
    }
    return $healthlinks;
  }

  function main()
  {
    \bbsengine6\session\start();
    
    \bbsengine6\setcurrentsite("achilles");
    \bbsengine6\setcurrentpage("index");
    \bbsengine6\setcurrentaction("view");
    \bbsengine6\setreturnto(\bbsengine6\getcurrenturi());
//    \bbsengine6\clearpageprotocol();

    $title = "achilles - a project to study manufactured free glutamic acid (aka monosodium glutamate (MSG)";

//    $page = \bbsengine6\getpage($title);
    $healthlinks = $this->gethealthlinks();
//    \bbsengine6\logentry("healthlinks=".var_export($healthlinks, true));

//    $tmpl = getsmarty();
//    $tmpl->assign("healthlinks", $healthlinks);

    $data = [];

    $metadata = [];
/*
    $metadata["og:description"] = "Project Achilles studies the effects of manufactured free glutamic acid (aka mono-sodium glutamate and MSG) on the human immune system";
    $metadata["og:title"] = $title;
    $metadata["og:type"] = "website";
    $metadata["og:url"] = 'http:'.ACHILLESURL;
    $metadata["keywords"] = "project achilles, manufactured free glutamic acid, monosodium glutamate, msg, nutrition, health, diet";
    $metadata["Generator"] = "PEAR HTML_Page2 via bbsengine4";
*/
    $data["healthlinks"] = $healthlinks;
    $data["metadata"] = $metadata;
    $data["pagetemplate"] = "index.tmpl"; // achilles-page.tmpl";

    $choices = [];
    if (\bbsengine6\member\lib\checkflag("SYSOP"))
    {
      $choices[] = ["name" => "add link", "title" => "add link to achilles sig", "url" => TEOSURL."achilles/add-link", "desc" => "add link to achilles sig"];
    }
    $data["choices"] = \zoid6\buildchoices($choices);

    \bbsengine6\displaypage($data, "index.tmpl");
    return;
  }
};

//print("foo!");

$a = new index();
$b = $a->main();
if (PEAR::isError($b))
{
  logentry("index.100: " . $b->toString());
  displayerrorpage($b->getMessage());
  exit;
}
?>
