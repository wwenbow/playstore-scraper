const request = require('request');
const cheerio = require('cheerio');
const progress = require('progress');
const fs = require('fs');
const commander = require('commander');
const spawn = require('child_process').spawnSync;
const https = require('https');
https.globalAgent.maxSockets = 10;

var printError = function (err, message) {
    console.error(message);
    console.trace();
    console.error(err.stack);
    console.error(err);
};

var getAppInfo = function($) {
    var appinfo = {};
    appinfo.pkg = $('div.details-wrapper').attr('data-docid');
    appinfo.icon = $('img[alt="Cover art"]').attr('src');
    appinfo.name = $('div.id-app-title').text();
    appinfo.developer = $('a.document-subtitle.primary').children().first().text();
    appinfo.genre = $('span[itemprop="genre"]').text();
    var rated = $('img.content-rating-badge').attr('alt');
    if (!rated) {
        appinfo.rated = 'Unrated';
    } else {
        appinfo.rated = rated;
    }
    var score = $('div.score').text();
    if (!score) {
        appinfo.score = 'Unscored';
    } else {
        appinfo.score = score;
    }

    return appinfo;
};

var getSimilarItems = function($) {
    var similar_items = [];
    var cards = $('div.rec-cluster').first().children('.cards.id-card-list').children('.card')
    cards.map(function() {
        similar_items.push($(this).attr('data-docid'));
    });
    return similar_items;
};

var main = function(){
    commander
        .version('1.0')
        .option('-i --input [in]', 'input package list [packages.txt]', 'packages.txt')
        .option('-o --output <out>', 'output directory')
        .option('-f --force', 'force')
        .parse(process.argv);

    if (commander.force) {
        spawn('rm', ['-rf', commander.output]);
    }
    fs.mkdirSync(commander.output);

    var baseurl = 'https://play.google.com/store/apps/details';
    var country = 'ph';

    var pkgfile = fs.readFileSync(commander.input,'utf8').split('\n');
    var pkgs = pkgfile.splice(0, pkgfile.length-1);
    
    var bar = new progress('  scraping [:bar] :percent eta-:etas elapsed-:elapsed  ', {total: pkgs.length});

    pkgs.forEach(function(pkg) {
        var url = baseurl + '?id=' + pkg + '&gl=' + country;

        request(url, function (err, response, html) {
            if (!err) {
                var $ = cheerio.load(html);
                var appinfo = getAppInfo($);
                appinfo.similar = getSimilarItems($);

                if (response.statusCode == 200) {
                    fs.appendFile(commander.output + '/appdata.json', JSON.stringify(appinfo) + '\n', function (err) {
                        if (err) {
                            printError(err, 'error writing appdata file');
                            process.exit(1);
                        }
                        bar.tick();
                        if (bar.complete) {
                            process.exit(0);
                        }
                    });
                } else {
                    fs.appendFile(commander.output + '/blacklist.txt', pkg + '\n', function (err) {
                        if (err) {
                            printError(err, 'error writing blacklist file');
                            process.exit(1);
                        }
                        bar.tick();
                        if (bar.complete) {
                            process.exit(0);
                        }
                    });
                }
            }
            else {
                printError(err, 'error accessing ' + url);
                process.exit(1);
            }
        });
    });
};

if (require.main === module) {
    main();
}
