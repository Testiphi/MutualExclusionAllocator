"""Safety and layout tests independent of private screenshots/OCR packages."""
from copy import deepcopy
import unittest
from backend.map_layout import parse_map_layout

PAIRS=[('花都疾驰','铁塔飞跃'),('热带天堂','地狱谷'),('季风秘境','碎石山路'),
       ('海港博物馆','海洋爆冲'),('古老斗技场','旧时风情')]
CATALOG={'tracks':[dict(big=b,small=s) for b,s in PAIRS]}


def row(text,cx,y,w=64,h=20,confidence=.99):
    return dict(text=text,confidence=confidence,box=[cx-w/2,y,w,h])


def qualifier(expanded=3,pairs=PAIRS):
    # Native published slot locations; do not import parser calibration.
    centers={1:[259,849,963,1077,1191],2:[120,373,963,1077,1191],
             3:[120,234,487,1077,1191],4:[120,234,348,601,1191],
             5:[120,234,348,462,715]}[expanded]
    words=[dict(text='资格赛',confidence=.99,box=[62,86,110,52])]
    for i,((big,small),cx) in enumerate(zip(pairs,centers),1):
        words += [row(big,cx,216 if i==expanded else 221,116 if i==expanded else 64,36 if i==expanded else 20),
                  row(small,cx,245 if i==expanded else 237,68 if i==expanded else 54,24 if i==expanded else 18)]
    return words


def cards(title='资格赛结果',pairs=PAIRS):
    words=[dict(text=title,confidence=.99,box=[90,105,190,52])]
    for (big,small),cx in zip(pairs,[237,522,807,1092,1377]):
        words += [row(big,cx,320,90,30),row(small,cx-12,344,62,22)]
    return words


def challenge(split=False):
    words=[dict(text='挑战',confidence=.99,box=[70,107,95,57])]
    if split:words += [row(PAIRS[0][0],477,284,80,28),row(PAIRS[0][1],565,284,80,28)]
    else:words += [row('花都疾驰 铁塔飞跃',521,284,200,28)]
    for (big,small),cx in zip(PAIRS[1:],[1039,1179,1319,1459]):
        words += [row(big,cx,357,78,30),row(small,cx,378,65,22)]
    return words


def opponent():
    words=[row('对手信息',1000,110,210,60)]
    for (big,small),cx in zip(PAIRS,[320,655,990,1325,1660]):
        words += [row(big,cx,390,120,36),row(small,cx,445,90,26)]
    return words


def settlement(title='防御结果',pairs=PAIRS):
    words=[row(title,180 if title=='防御结果' else 790,280,180,48)]
    for i,(big,small) in enumerate(pairs):
        words += [row(big,795,389+i*76,100,32),row(small,795,414+i*76,82,26)]
        # Even catalog-like strings among car/timing columns cannot supply maps.
        words += [row(PAIRS[(i+1)%5][0],280,389+i*76),row('00:35.366',580,400+i*76),row('00:34.757',990,400+i*76)]
    return words


def detail_result():
    words=[row('挑战详情',1280,55,232,67),row('获胜',1240,225,168,95),row('对手信息',485,992,246,80)]
    for i,(big,small) in enumerate(PAIRS):
        words += [row(big,1240,391+i*107,160,53),row(small,1240,434+i*107,135,41)]
    return words


class MapLayoutTests(unittest.TestCase):
    def parse(self,words,size=(1280,720),catalog=CATALOG,**kwargs):
        return parse_map_layout(size,words,catalog,**kwargs)

    def assert_complete(self,result,pairs=PAIRS):
        self.assertEqual(result['status'],'complete',result)
        self.assertEqual([(s['big'],s['small']) for s in result['slots']],pairs)
        self.assertEqual([s['slot'] for s in result['slots']],[1,2,3,4,5])
        self.assertTrue(result['needs_user_confirmation'])

    def test_every_expanded_slot_without_selection_buttons(self):
        for slot in range(1,6):
            with self.subTest(slot=slot):self.assert_complete(self.parse(qualifier(slot)))

    def test_action_text_and_its_absence_do_not_gate_map_observation(self):
        words=qualifier()
        buttons=[row('选择车辆',822,506),row('更换车辆',822,506)]
        expected=self.parse(words)
        for button in buttons:self.assertEqual(self.parse(words+[button]),expected)

    def test_missing_second_map_never_shifts_third_to_second(self):
        words=[r for r in qualifier() if r['text'] not in PAIRS[1]]
        result=self.parse(words)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['slots'][1]['state'],'unresolved')
        self.assertEqual(result['slots'][2]['big'],PAIRS[2][0])
        self.assertEqual(result['diagnostics']['expanded_slot'],3)

    def test_missing_expanded_name_does_not_guess_anchor_from_remaining_count(self):
        words=[r for r in qualifier() if r['text'] not in PAIRS[2]]
        self.assertNotEqual(self.parse(words)['status'],'complete')

    def test_cards_missing_middle_preserves_later_real_slots(self):
        words=[r for r in cards() if r['text'] not in PAIRS[1]]
        result=self.parse(words,(1567,1080))
        self.assertEqual(result['slots'][1]['state'],'unresolved')
        self.assertEqual(result['slots'][2]['big'],PAIRS[2][0])
        self.assertEqual(result['slots'][4]['big'],PAIRS[4][0])

    def test_result_and_defense_layouts_support_tablet_proportions(self):
        for title in ['资格赛结果','资格赛失利','防御']:
            with self.subTest(title=title):self.assert_complete(self.parse(cards(title),(1567,1080)))

    def test_challenge_inline_and_split_header_preserve_ordinal(self):
        for split in [False,True]:
            with self.subTest(split=split):self.assert_complete(self.parse(challenge(split),(1567,1080)))

    def test_challenge_big_name_alone_never_completes_missing_small(self):
        words=challenge();words[1]['text']='花都疾驰'
        self.assertNotEqual(self.parse(words,(1567,1080))['status'],'complete')

    def test_challenge_and_defense_support_each_expanded_slot(self):
        left=[148,287,426,565]
        right=[1039,1179,1319,1459]
        for title,layout in [('挑战','challenge'),('防御','defense_cards')]:
            for index,center in enumerate([521,660,800,939,1079]):
                big,small=PAIRS[index]
                headers=([row(big+' '+small,center,284,166,28)],
                         [row(big,center-44,284,76,28),row(small,center+44,284,76,28)])
                side_words=[row(title,116,107),row('KIMERA',center-363,342),row('CC850',center+372,362)]
                for (side_big,side_small),cx in zip(PAIRS[:index]+PAIRS[index+1:],left[:index]+right[index:]):
                    side_words += [row(side_big,cx,357,78,29),row(side_small,cx,378,65,22)]
                for header in headers:
                    with self.subTest(title=title,slot=index+1,split=len(header)==2):
                        result=self.parse(side_words+header,(1567,1080))
                        self.assert_complete(result)
                        self.assertEqual(result['layout'],layout)
                        self.assertEqual(result['diagnostics']['expanded_slot'],index+1)
                self.assertNotEqual(self.parse(side_words,(1567,1080))['status'],'complete')

    def test_current_order_comes_from_positions_not_catalog_order(self):
        order=[PAIRS[4],PAIRS[1],PAIRS[3],PAIRS[0],PAIRS[2]]
        self.assert_complete(self.parse(qualifier(pairs=order)),order)

    def test_duplicate_reference_is_invalid_instead_of_first_match_wins(self):
        catalog=deepcopy(CATALOG);catalog['tracks'].append(catalog['tracks'][0])
        self.assertEqual(self.parse(qualifier(),catalog=catalog)['reason'],'duplicate_catalog_pair')

    def test_competing_catalog_match_remains_ambiguous(self):
        catalog=deepcopy(CATALOG);catalog['tracks'].append(dict(big='花都疾驰',small='铁塔飞越'))
        result=self.parse(qualifier(),catalog=catalog)
        self.assertEqual(result['slots'][0]['state'],'ambiguous')

    def test_unlisted_third_name_in_cell_is_conflict_not_ignored(self):
        result=self.parse(qualifier()+[row('完全未知地图',120,265)])
        self.assertEqual(result['slots'][0]['state'],'ambiguous')

    def test_cross_cell_pair_cannot_be_combined(self):
        words=qualifier();words[4]['box'][0]=1077-27
        self.assertNotEqual(self.parse(words)['status'],'complete')

    def test_exact_duplicate_ocr_is_not_a_new_physical_line(self):
        words=qualifier();self.assert_complete(self.parse(words+[deepcopy(words[1])]))

    def test_duplicate_map_in_two_slots_cannot_be_complete(self):
        order=[PAIRS[0],PAIRS[0],*PAIRS[2:]]
        self.assertNotEqual(self.parse(qualifier(pairs=order))['status'],'complete')

    def test_equal_height_lines_and_cell_boundary_do_not_get_arbitrary_order(self):
        words=cards();words[2]['box'][1]=words[1]['box'][1]
        self.assertNotEqual(self.parse(words,(1567,1080))['status'],'complete')
        words=qualifier();words[1]['box'][0]=174-32
        self.assertNotEqual(self.parse(words)['status'],'complete')

    def test_conflicting_title_and_modal_do_not_accept_background_maps(self):
        words=qualifier()+[dict(text='挑战',confidence=.99,box=[62,86,110,52])]
        self.assertEqual(self.parse(words)['reason'],'page_title_conflict')
        words=qualifier()+[row('重新开始',640,330,200,40)]
        self.assertEqual(self.parse(words)['reason'],'modal_overlay')

    def test_bad_inputs_abstain_without_crashing_or_stale_slots(self):
        for words in [None,[{}],[row('资'*257,100,100)],[row('资格赛',100,100,confidence=float('nan'))],
                      [dict(text='资格赛',confidence=True,box=[1,2,3,4])],
                      [dict(text='资格赛',confidence=.99,box=[1,2,-3,4])]]:
            with self.subTest(words=words):
                r=self.parse(words);self.assertEqual(r['status'],'rejected')
                self.assertTrue(all(s['big'] is None for s in r['slots']))
        for size in [(True,720),(3840,1080),(0,720),(1280,float('inf'))]:
            self.assertEqual(self.parse(qualifier(),size)['status'],'rejected')

    def test_no_mutation_and_server_catalog_binding_are_retained(self):
        words=qualifier();copy=deepcopy(words);catalog=deepcopy(CATALOG)
        result=self.parse(words,server='global',catalog_version='frozen-global')
        self.assert_complete(result);self.assertEqual(words,copy);self.assertEqual(catalog,CATALOG)
        self.assertEqual(result['server'],'global');self.assertEqual(result['catalog_version'],'frozen-global')
        self.assertNotIn('can_click',result);self.assertNotIn('action_ready',result)
        self.assertEqual(self.parse(words,server='other')['reason'],'invalid_server')

    def test_original_coordinate_scale_keeps_same_slots(self):
        words=qualifier(4)
        for item in words:item['box']=[x/2 for x in item['box']]
        self.assert_complete(self.parse(words,(640,360)))

    def test_opponent_modal_reads_five_columns_not_player_identity(self):
        words=opponent()+[row('用户ID',800,240),row('匿名玩家',300,230)]
        self.assert_complete(self.parse(words,(2000,1000)))

    def test_opponent_missing_column_does_not_shift_later_maps(self):
        words=[x for x in opponent() if x['text'] not in PAIRS[1]]
        result=self.parse(words,(2000,1000));self.assertEqual(result['slots'][1]['state'],'unresolved')
        self.assertEqual(result['slots'][2]['big'],PAIRS[2][0]);self.assertNotEqual(result['status'],'complete')

    def test_vertical_attack_and_defense_results_read_top_to_bottom(self):
        for title in ['防御结果','挑战获胜','挑战失利','挑战胜利','挑战失败']:
            with self.subTest(title=title):self.assert_complete(self.parse(settlement(title),(1567,1080)))

    def test_missing_result_row_preserves_its_empty_ordinal(self):
        words=settlement();words=[x for x in words if not (453<x['box'][1]+x['box'][3]/2<529 and 660<x['box'][0]+x['box'][2]/2<940)]
        result=self.parse(words,(1567,1080));self.assertEqual(result['slots'][1]['state'],'unresolved')
        self.assertEqual(result['slots'][2]['big'],PAIRS[2][0]);self.assertEqual(result['slots'][4]['big'],PAIRS[4][0])

    def test_extra_result_name_or_sixth_map_row_is_not_silently_ignored(self):
        result=self.parse(settlement()+[row('完全未知地图',795,430)],(1567,1080))
        self.assertEqual(result['slots'][0]['state'],'ambiguous')
        result=self.parse(settlement()+[row('热带天堂',795,790),row('地狱谷',795,815)],(1567,1080))
        self.assertNotEqual(result['status'],'complete')

    def test_opponent_button_is_not_a_modal_title_and_real_modal_veto_remains(self):
        words=opponent();words[0]['box'][1]=900
        self.assertNotEqual(self.parse(words,(2000,1000))['status'],'complete')
        result=self.parse(opponent()+[row('重新开始',1000,500,200,45)],(2000,1000))
        self.assertEqual(result['reason'],'modal_overlay')

    def test_result_conflict_and_duplicate_maps_never_complete(self):
        words=settlement()+[row('对手信息',780,100,180,50)]
        self.assertEqual(self.parse(words,(1567,1080))['reason'],'page_title_conflict')
        self.assertNotEqual(self.parse(settlement(pairs=[PAIRS[0],PAIRS[0],*PAIRS[2:]]),(1567,1080))['status'],'complete')

    def test_challenge_detail_modal_uses_its_own_five_row_grid(self):
        result=self.parse(detail_result(),(2556,1179));self.assert_complete(result)
        self.assertEqual(result['layout'],'challenge_detail_rows')

    def test_unfinished_time_and_score_columns_do_not_change_maps(self):
        words=detail_result()+[row('未完成',1556,520,126,54),row('00:23.519',910,520,150,40)]
        self.assert_complete(self.parse(words,(2556,1179)))

    def test_detail_missing_second_row_stays_empty_not_renumbered(self):
        words=[r for r in detail_result() if r['text'] not in PAIRS[1]]
        result=self.parse(words,(2556,1179));self.assertEqual(result['slots'][1]['state'],'unresolved')
        self.assertEqual(result['slots'][2]['big'],PAIRS[2][0]);self.assertNotEqual(result['status'],'complete')

    def test_victory_text_without_detail_title_is_not_sufficient(self):
        words=[r for r in detail_result() if r['text']!='挑战详情']
        self.assertNotEqual(self.parse(words,(2556,1179))['status'],'complete')


if __name__=='__main__':unittest.main(verbosity=2)
