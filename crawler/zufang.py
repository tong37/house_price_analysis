# reference: https://www.zhihu.com/question/443457100/answer/1721778654
# 结果强卡<offset≤2999,limit≤30>, 在不考虑重复的情况下最多只能拿到3029/38141个结果, 实际去重后在2860附近,
# 故需要通过条件组合对结果进行细粒度分流, 确保每个组合条件下的结果在3k以内, 且所有组合加起来没有遗漏, 最后再将所有结果合并.
# 组合条件: <区域>, 将区域降到商圈级别即可保证每个筛选结果均在3k以内.
import json
import time
import requests
import os.path as op
from city import update_city
from config import zufang_api, zufang_json, use_cache, max_retry_turns

# headers
headers = {
    "Referer": "homepage1",
    "User-Agent": "Beike2.50.1;Xiaomi MI+6; Android 5.1.1; ABtestEnable false",
    "Host": "app.api.ke.com"
}
# target city
city_id = 370200  # beijing
city_abbr = "qd"


# Parse Rentplat format api
def get_api_data(url, params):
    res = requests.get(url, params=params, headers=headers)
    # assert res.json()["msg"] == "OK", "Failed on {}\t{}".format(api_url, params)
    return res.json()["data"]


# Update $total_rents (totalCount of zufang, which changes frequently)
def update_total_rents(city_id):
    return get_api_data(zufang_api, {"city_id": city_id})["total"]


# Crawl & Save all ershoufang house infos to a dict
# rco11 for 最新上架, rco21 for 价格, rco31 for 面积
def get_zufang_info(city_id, city, district_dict, bizcircle_list):
    # Patterns: (Complexity: Hard)
    # 1) Σ$bc_total_houses ≈ $total_rents - 2k; (API data is incomplete)
    # 2) every $bc_total_rents is less than 3k (the result size upper bound in a conditional search);
    # 3) about 20% replications are found when crawling, so deploy $rent_dict and use field "house_code"
    #    to remove duplicates;
    # 4) results are uncertain, totally randomized: $bc_total_rents varies by a large margin when payload["offset"]
    #    changes, and every time requesting a same url can also get very different results, so I rerun the crawler
    #    3 times for each bizcircle, then merge results with key "house_code" to approximate full result.
    payload = {
        "city_id": city_id,
        "condition": "",  # rco11 rco21 rco31和空 替换着多搞几次
        "offset": 0,  # 上界: 2999
        "limit": 30,  # 上界: 30
        "feed_query_id": "",
        "from": "default_list",
        "page_uicode": "matrix_homepage",
    }
    start_t, total_cnt, repl_cnt, rent_dict = time.perf_counter(), 0, 0, {}
    for idx, bizcircle in enumerate(bizcircle_list):
        total_rents = update_total_rents(city_id)
        payload["condition"] = bizcircle.quan_pin
        data = get_api_data(zufang_api, payload)
        bc_total_rents = data["total"]
        district_name = ",".join(district_dict[did].name for did in bizcircle.district_id)
        # print("\r{:>3}) [{}-{}] Total: {}/{}/{} || Time: {:.1f}s"
        #       .format(idx + 1, bizcircle.name, district_name,
        #               bc_total_rents, cnt, total_rents, time.perf_counter() - start_t), end="")
        turn_id, bc_rent_dict, bc_start_t = 0, {}, time.perf_counter()
        while turn_id < max_retry_turns:
            if len(bc_rent_dict) >= bc_total_rents and bc_total_rents > 0:
                break
            bc_total_cnt, page_id, payload["offset"] = 0, 1, 0
            while True:
                data = get_api_data(zufang_api, payload)
                rent_list = data["list"]
                for rent in rent_list:
                    bc_rent_dict[rent["house_code"]] = rent
                bc_total_cnt += len(rent_list)
                print("\r{:>3}) [{}-{}] [Turn{}]: {}/{}/{}, Pages {} || Time: {:.1f}s"
                      .format(idx + 1, bizcircle.name, district_name,
                              turn_id + 1, len(bc_rent_dict), bc_total_cnt, bc_total_rents, page_id,
                              time.perf_counter() - bc_start_t), end="")
                if len(rent_list) == 0:
                    break
                page_id += 1
                payload["offset"] += payload["limit"]
                payload["feed_query_id"] = data["feed_query_id"]  # 这一步很重要
            turn_id += 1
        print()
        last_rents = len(rent_dict)
        for house_code, rent in bc_rent_dict.items():
            rent_dict[house_code] = rent
        total_cnt += bc_total_rents
        repl_cnt = total_cnt - len(rent_dict)
        rest_cnt = total_rents - total_cnt
        speed = (len(rent_dict) - last_rents) / (time.perf_counter() - bc_start_t)
        print("\r{:>3}) [{}-{}] Total: {}/{}/{}, Repl {} || Current: {}/{} || Time: {:.1f}s/{:.1f}s, "
              "Speed {:.1f}/s, ETA {}"
              .format(idx + 1, bizcircle.name, district_name,
                      len(rent_dict), total_cnt, total_rents, repl_cnt,
                      len(rent_dict) - last_rents, bc_total_rents,
                      time.perf_counter() - bc_start_t, time.perf_counter() - start_t,
                      speed, "{:.1f}s".format(rest_cnt / speed) if speed > 0 else "---"))
    # Calc replication_ratio
    print("repl_ratio: {:.1f}%".format(repl_cnt / len(rent_dict) * 100))
    json.dump(rent_dict, open(zufang_json.format(city.abbr), "w+", encoding="utf-8"), ensure_ascii=False, indent=4)
    return rent_dict


if __name__ == "__main__":
    city, district_dict, bizcircle_list = update_city(city_id, city_abbr)
    print()
    json_file = zufang_json.format(city_abbr)
    rent_dict = json.load(open(json_file, encoding="utf-8")) if use_cache and op.exists(json_file) \
        else get_zufang_info(city_id, city, district_dict, bizcircle_list)
    print("Crawled & Saved {} zufang infos.".format(len(rent_dict)))

