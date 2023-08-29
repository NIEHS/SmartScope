from pathlib import Path

from Smartscope.lib.preprocessing_methods import get_CTFFIN4_data, get_CTFFIN4_data_2


ctf_text = '/home/yuant2/nieh/build_smartscope/data/smartscope/BaiY/20230208_HQF-JAL-IKY/1_HQFA_1/HQFA_1_square136_hole16_0_hm/ctf.txt'
ctf = get_CTFFIN4_data(ctf_text)
print(ctf)

ctf_text = '/home/yuant2/nieh/build_smartscope/data/smartscope/smartscope_testfiles/HQFA_1_square155_hole36_0_hm/ctf.txt'

ctf = get_CTFFIN4_data(ctf_text)
print(ctf)

ctf = get_CTFFIN4_data_2(ctf_text)
print(ctf)