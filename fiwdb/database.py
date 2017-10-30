"""
Module of utilities for handling FIW DB.

Methods to download PIDs using URL, load Anns and LUTs, along with metadata (e.g., gender, mids, pair lists).
"""
import glob
import pandas as pd
import numpy as np
import common.image as imutils
from urllib.error import URLError, HTTPError
import common.io as io
import common.log as log
from common.io import sys_home as dir_home

# TODO urllib.request to handle thrown exceptions <p>Error: HTTP Error 403: Forbidden</p>
# TODO modify fold2set with optional args that spefify which fold merges into which set (i.e., currently hard coded).

logger = log.setup_custom_logger(__name__, f_log='fiwdb.log', level=log.INFO)
logger.info('FIW-DB')

dir_db = str(dir_home()) + "/Dropbox/Families_In_The_Wild/Database/"


def download_images(f_pid_csv=dir_db + "FIW_PIDs_new.csv", dir_out=dir_db + "fiwimages/"):
    """
    Download FIW database by referencing PID LUT. Each PID is listed with corresponding URL. URL is downloaded and
    saved as <FID>/PID.jpg
    :type f_pid_csv: object
    :type dir_out: object
    """
    logger.info("FIW-DB-- Download_images!\n Source: {}\n Destination: {}".format(f_pid_csv, dir_out))
    # load urls (image location), pids (image name), and fids (output subfolder)
    df_pid = load_pid_lut(str(f_pid_csv))

    df_io = df_pid[['FIDs', 'PIDs', 'URL']]

    logger.info("{} photos to download".format(int(df_io.count().mean())))

    for i, img_url in enumerate(df_io['URL']):
        if i == 100:
            return
        try:
            f_out = str(dir_out) + df_io['FIDs'][i] + "/" + df_io['PIDs'][i] + ".jpg"
            img = imutils.url_to_image(img_url)
            logger.info("Downloading {}\n{}\n".format(df_io['PIDs'][i], img_url))
            imutils.saveimage(f_out, img)
        except Exception as e:
            logger.error("Error with {}\n{}\n".format(df_io['PIDs'][i], img_url))
            error_message = "<p>Error: %s</p>\n" % str(e)
            logger.error(error_message)
        except HTTPError as e:
            logger.error("The server couldn't fulfill the request.")
            logger.error("Error code: ", e.code)
        except URLError as e:
            logger.error("Failed to reach a server.")
            logger.error("Reason: ", e.reason)


def get_unique_pairs(ids_in):
    """

    :param ids_in:
    :return:
    """
    ids = [(p1, p2) if p1 < p2 else (p2, p1) for p1, p2 in zip(list(ids_in[0]), list(ids_in[1]))]
    return list(set(ids))


def load_rid_lut(f_csv=dir_db + "FIW_RIDs.csv"):
    """

    :param f_csv:
    :return:
    """

    return pd.read_csv(f_csv, delimiter=',')


def load_pid_lut(f_csv=dir_db + "FIW_PIDs_new.csv"):
    """

    :param f_csv:
    :return:
    """
    return pd.read_csv(f_csv, delimiter='\t')


def load_fid_lut(f_csv=dir_db + "FIW_FIDs.csv"):
    """
    Load FIW_FIDs.csv-- FID- Surname LUT
    :param f_csv:
    :return:
    """
    return pd.read_csv(f_csv, delimiter='\t')


def load_fids(dirs_fid):
    """
    Function loads fid directories and labels.
    :param dirs_fid: root folder containing FID directories (i.e., F0001-F1000)
    :return: (list, list):  (fid filepaths and fid labels of these)
    """
    dirs = glob.glob(dirs_fid + 'F????/')
    fid_list = [d[-6:-1] for d in dirs]

    return dirs, fid_list


def load_mids(dirs_fid, f_csv='mid.csv'):
    """
    Load CSV file containing member information, i.e., {MID : ID, Name, Gender}
    :type f_csv:        file name of CSV files containing member labels
    :param dirs_fid:    root folder containing FID/MID/ folders of DB.

    :return:
    """

    return [pd.read_csv(d + f_csv) for d in dirs_fid]


def load_relationship_matrices(dirs_fid, f_csv='relationships.csv'):
    """
    Load CSV file containing member information, i.e., {MID : ID, Name, Gender}
    :type f_csv:        file name of CSV files containing member labels
    :param dirs_fid:    root folder containing FID/MID/ folders of DB.

    :return:
    """
    df_relationships = [pd.read_csv(d + f_csv) for d in dirs_fid]

    for i in range(len(df_relationships)):
        # df_relationships = [content.ix[:, 1:len(content) + 1] for content in df_rel_contents]

        df_relationships[i].index = range(1, len(df_relationships[i]) + 1)
        df_relationships[i] = df_relationships[i].ix[:, 1:len(df_relationships[i]) + 1]

    return df_relationships


def parse_relationship_matrices(df_mid):
    """
    Parses out relationship matrix from MID dataframe.

    :return:
    """
    # df_relationships = [content.ix[:, 1:len(content) + 1] for content in df_rel_contents]
    df_relationships = df_mid
    df_relationships.index = range(1, len(df_relationships) + 1)
    df_relationships = df_relationships.ix[:, 1:len(df_relationships) + 1]

    return np.array(df_relationships)


def set_pairs(mylist, ids_in, kind, fid):
    """
    Adds items to mylist of unique pairs.
    :param mylist:
    :param ids_in:
    :param kind:
    :param fid:
    :return:
    """
    ids = get_unique_pairs(ids_in)
    for i in enumerate(ids):
        print(i)
        indices = list(np.array(i[1]) + 1)
        mylist.append(Pair(mids=indices, fid=fid, kind=kind))
        del indices
    return mylist


def specify_gender(rel_mat, genders, gender):
    """
    :param rel_mat:
    :param genders: list of genders
    :param gender:  gender to search for {'Male' or Female}
    :type gender:   str
    :return:
    """
    ids_not = [j for j, s in enumerate(genders) if gender not in s]
    rel_mat[ids_not, :] = 0
    rel_mat[:, ids_not] = 0

    return rel_mat


def folds_to_sets(f_csv=dir_db + 'journal_data/Pairs/folds_5splits/', dir_out=dir_db + "journal_data/Pairs/sets/"):
    """ Method used to merge 5 fold splits into 3 sets for RFIW (train, val, and test)"""

    f_in = glob.glob(f_csv + '*-folds.csv')

    for file in f_in:
        # each list of pairs <FOLD, LABEL, PAIR_1, PAIR_2>
        f_name = io.file_base(file)
        print("\nProcessing {}\n".format(f_name))

        df_pairs = pd.read_csv(file)

        # merge to form train set
        df_train = df_pairs[(df_pairs['fold'] == 1) | (df_pairs['fold'] == 5)]
        df_train.to_csv(dir_out + "train/" + f_name.replace("-folds", "-train") + ".csv")

        # merge to form val set
        df_val = df_pairs[(df_pairs['fold'] == 2) | (df_pairs['fold'] == 4)]
        df_val.to_csv(dir_out + "val/" + f_name.replace("-folds", "-val") + ".csv")

        # merge to form test set
        df_test = df_pairs[(df_pairs['fold'] == 3)]
        df_test.to_csv(dir_out + "test/" + f_name.replace("-folds", "-test") + ".csv")

        # print stats
        print("{} Training;\t {} Val;\t{} Test".format(df_train['fold'].count(), df_val['fold'].count(),
                                                       df_test['fold'].count()))


class Pairs(object):
    def __init__(self, pair_list, kind=''):
        self.df_pairs = Pairs.list2table(pair_list)
        # self.df_pairs = pd.DataFrame({'p1': p1, 'p2': p2})
        self.type = kind
        self.npairs = len(self.df_pairs)

    @staticmethod
    def list2table(pair_list):
        p1 = ['{}/MID{}'.format(pair.fid, pair.mids[0]) for pair in pair_list]
        p2 = ['{}/MID{}'.format(pair.fid, pair.mids[1]) for pair in pair_list]

        return pd.DataFrame({'p1': p1, 'p2': p2})

    def write_pairs(self, f_path):
        """
        :param f_path: filepath (CSV file) to store all pairs
        :type f_path: str
        :return: None
        """
        self.df_pairs.to_csv(f_path, index=False)

        # def __str__(self):
        #     return "FID: {}\nMIDS: ({}, {})\tType: {}".format(self.fid, self.mids[0], self.mids[1], self.type)

class Pair(object):
    def __init__(self, mids, fid, kind=''):
        self.mids = mids
        self.fid = fid
        self.type = kind

    def __str__(self):
        return "FID: {} ; MIDS: ({}, {}) ; Type: {}".format(self.fid, self.mids[0], self.mids[1], self.type)

    def __key(self):
        return self.mids[0], self.mids[1], self.fid, self.type

    # def __eq__(self, other):
    #     return self.fid == other.fid and self.mids[0] == other.mids[0] and self.mids[1] == other.mids[1]

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    def __lt__(self, other):
        return np.uint(self.fid[1::]) < np.uint(other.fid[1::])

